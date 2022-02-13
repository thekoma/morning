#!/bin/bash
if [[ $GITHUB_REF == refs/tags/* ]]; then
  export GIT_TAG=${GITHUB_REF#refs/tags/}
else
  export GIT_BRANCH=${GITHUB_REF#refs/heads/}
fi

if [[ -n "${GIT_TAG}" ]]; then
  docker buildx build --progress plain --pull --push --platform "${DOCKER_BUILD_PLATFORM}" -t ghcr.io/${REPOSITORY}:${GIT_TAG} .
elif [[ -n "${GIT_BRANCH}" ]]; then
  if [[ "${GIT_BRANCH}" == "main" ]]; then
    docker buildx build --progress plain --pull --push --platform "${DOCKER_BUILD_PLATFORM}" -t ghcr.io/${REPOSITORY}:latest .
  else
    docker buildx build --progress plain --pull --push --platform "${DOCKER_BUILD_PLATFORM}" -t ghcr.io/${REPOSITORY}:${GIT_BRANCH} .
  fi
else
  :
fi