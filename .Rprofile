local({
  profile <- Sys.getenv("R_PROFILE_USER", unset = ".Rprofile")
  project <- dirname(normalizePath(profile, mustWork = TRUE))
  Sys.setenv(RENV_PROJECT = project)
  source(file.path(project, "renv/activate.R"))
})
