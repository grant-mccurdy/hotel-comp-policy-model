from __future__ import annotations

import argparse
import json
import os
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from common import MANIFEST_DIR, PROJECT_ROOT, ensure_dirs, utc_now_iso, write_json
from load_snowflake_warehouse import connector_connection


INTEGRATION_MANIFEST_PATH = MANIFEST_DIR / "s3_snowflake_integration_manifest.json"
DEFAULT_PREFIX = "hotel-comp-policy-model"
DEFAULT_ROLE_NAME = "hotel-comp-snowflake-stage-role"
DEFAULT_POLICY_NAME = "hotel-comp-snowflake-stage-policy"
DEFAULT_INTEGRATION = "HOTEL_COMP_S3_INTEGRATION"


def required_bucket(value: str | None) -> str:
    bucket = value or os.environ.get("HOTEL_COMP_S3_BUCKET")
    if not bucket:
        raise RuntimeError("Provide --bucket or set HOTEL_COMP_S3_BUCKET.")
    return bucket


def clean_prefix(prefix: str) -> str:
    return prefix.strip("/")


def account_id() -> str:
    return boto3.client("sts").get_caller_identity()["Account"]


def ensure_bucket(bucket: str, region: str) -> None:
    s3 = boto3.client("s3", region_name=region)
    try:
        s3.head_bucket(Bucket=bucket)
        print(f"Bucket exists: {bucket}")
    except ClientError:
        kwargs: dict[str, Any] = {"Bucket": bucket}
        if region != "us-east-1":
            kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}
        s3.create_bucket(**kwargs)
        print(f"Created bucket: {bucket}")
    s3.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    s3.put_bucket_encryption(
        Bucket=bucket,
        ServerSideEncryptionConfiguration={
            "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
        },
    )
    s3.put_bucket_versioning(Bucket=bucket, VersioningConfiguration={"Status": "Enabled"})


def initial_trust_policy(aws_account_id: str) -> dict[str, Any]:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": f"arn:aws:iam::{aws_account_id}:root"},
                "Action": "sts:AssumeRole",
            }
        ],
    }


def snowflake_trust_policy(snowflake_user_arn: str, external_id: str) -> dict[str, Any]:
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": snowflake_user_arn},
                "Action": "sts:AssumeRole",
                "Condition": {"StringEquals": {"sts:ExternalId": external_id}},
            }
        ],
    }


def s3_policy(bucket: str, prefix: str) -> dict[str, Any]:
    clean = clean_prefix(prefix)
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:GetObjectVersion"],
                "Resource": [f"arn:aws:s3:::{bucket}/{clean}/*"],
            },
            {
                "Effect": "Allow",
                "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
                "Resource": [f"arn:aws:s3:::{bucket}"],
                "Condition": {"StringLike": {"s3:prefix": [f"{clean}/*", clean]}},
            },
        ],
    }


def ensure_iam_role_and_policy(bucket: str, prefix: str, role_name: str, policy_name: str) -> tuple[str, str]:
    iam = boto3.client("iam")
    aws_account_id = account_id()
    try:
        role = iam.get_role(RoleName=role_name)["Role"]
        print(f"IAM role exists: {role_name}")
    except ClientError:
        role = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(initial_trust_policy(aws_account_id)),
            Description="Snowflake external stage read role for hotel comp policy model S3 data lake.",
        )["Role"]
        print(f"Created IAM role: {role_name}")

    policy_arn = f"arn:aws:iam::{aws_account_id}:policy/{policy_name}"
    try:
        iam.get_policy(PolicyArn=policy_arn)
        default_version = iam.get_policy(PolicyArn=policy_arn)["Policy"]["DefaultVersionId"]
        versions = iam.list_policy_versions(PolicyArn=policy_arn)["Versions"]
        non_default = [version["VersionId"] for version in versions if not version["IsDefaultVersion"]]
        while len(versions) >= 5 and non_default:
            iam.delete_policy_version(PolicyArn=policy_arn, VersionId=non_default.pop(0))
            versions = iam.list_policy_versions(PolicyArn=policy_arn)["Versions"]
        iam.create_policy_version(
            PolicyArn=policy_arn,
            PolicyDocument=json.dumps(s3_policy(bucket, prefix)),
            SetAsDefault=True,
        )
        print(f"Updated IAM policy: {policy_name} (previous default {default_version})")
    except ClientError:
        iam.create_policy(
            PolicyName=policy_name,
            PolicyDocument=json.dumps(s3_policy(bucket, prefix)),
            Description="Allow Snowflake to read hotel comp policy model raw S3 artifacts.",
        )
        print(f"Created IAM policy: {policy_name}")

    attached = iam.list_attached_role_policies(RoleName=role_name)["AttachedPolicies"]
    if not any(policy["PolicyArn"] == policy_arn for policy in attached):
        iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
        print(f"Attached policy to role: {policy_name}")
    return role["Arn"], policy_arn


def create_storage_integration(integration: str, role_arn: str, bucket: str, prefix: str) -> dict[str, str]:
    clean = clean_prefix(prefix)
    connection = connector_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            f"""
            CREATE OR REPLACE STORAGE INTEGRATION {integration}
              TYPE = EXTERNAL_STAGE
              STORAGE_PROVIDER = 'S3'
              ENABLED = TRUE
              STORAGE_AWS_ROLE_ARN = '{role_arn}'
              STORAGE_ALLOWED_LOCATIONS = ('s3://{bucket}/{clean}/');
            """
        )
        cursor.execute(f"GRANT USAGE ON INTEGRATION {integration} TO ROLE HOTEL_COMP_DEV_ROLE")
        cursor.execute(f"DESC INTEGRATION {integration}")
        rows = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()
    return {row[0]: row[2] for row in rows}


def update_trust(role_name: str, snowflake_user_arn: str, external_id: str) -> None:
    iam = boto3.client("iam")
    iam.update_assume_role_policy(
        RoleName=role_name,
        PolicyDocument=json.dumps(snowflake_trust_policy(snowflake_user_arn, external_id)),
    )
    print(f"Updated IAM trust policy for Snowflake user: {role_name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap AWS S3 data lake and Snowflake storage integration.")
    parser.add_argument("--bucket", default=None, help="S3 bucket. Defaults to HOTEL_COMP_S3_BUCKET.")
    parser.add_argument("--prefix", default=os.environ.get("HOTEL_COMP_S3_PREFIX", DEFAULT_PREFIX))
    parser.add_argument("--region", default=os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1")
    parser.add_argument("--role-name", default=DEFAULT_ROLE_NAME)
    parser.add_argument("--policy-name", default=DEFAULT_POLICY_NAME)
    parser.add_argument("--integration", default=os.environ.get("SNOWFLAKE_S3_INTEGRATION", DEFAULT_INTEGRATION))
    args = parser.parse_args()

    ensure_dirs()
    try:
        bucket = required_bucket(args.bucket)
        ensure_bucket(bucket, args.region)
        role_arn, policy_arn = ensure_iam_role_and_policy(bucket, args.prefix, args.role_name, args.policy_name)
        integration_props = create_storage_integration(args.integration, role_arn, bucket, args.prefix)
        snowflake_user_arn = integration_props["STORAGE_AWS_IAM_USER_ARN"]
        external_id = integration_props["STORAGE_AWS_EXTERNAL_ID"]
        update_trust(args.role_name, snowflake_user_arn, external_id)
    except NoCredentialsError:
        print("ERROR: AWS credentials are not configured. Run `aws login` or configure an AWS profile, then retry.")
        return 1
    except (BotoCoreError, ClientError, RuntimeError, KeyError) as error:
        print(f"ERROR: S3/Snowflake integration bootstrap failed: {error}")
        return 1

    manifest = {
        "generated_at": utc_now_iso(),
        "bucket": bucket,
        "prefix": clean_prefix(args.prefix),
        "aws_region": args.region,
        "iam_role_name": args.role_name,
        "iam_role_arn": role_arn,
        "iam_policy_arn": policy_arn,
        "snowflake_integration": args.integration,
        "snowflake_external_id_registered": True,
        "source_contract": "S3 data lake landing zone -> Snowflake storage integration -> external stage COPY INTO",
    }
    write_json(INTEGRATION_MANIFEST_PATH, manifest)
    print(f"Wrote integration manifest: {INTEGRATION_MANIFEST_PATH.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
