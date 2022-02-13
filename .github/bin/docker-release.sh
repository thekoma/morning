#!/bin/bash
echo CONTEXT
echo $GITHUB_CONTEXT
echo env
env


echo "$GHCR_PASSWORD"   | docker login ghcr.io -u "$GHCR_USERNAME"   --password-stdin


export GHCR_ORG="thekoma"
export GHCR_PROJECT="morning"
export GHCR_REPO="ghcr.io/${GHCR_ORG}/${GHCR_PROJECT}"

if [[ $GITHUB_REF == refs/tags/* ]]; then
  export GIT_TAG=${GITHUB_REF#refs/tags/}
else
  export GIT_BRANCH=${GITHUB_REF#refs/heads/}
fi

if [[ -n "${GIT_TAG}" ]]; then
  docker buildx build --progress plain --pull --push --platform "${DOCKER_BUILD_PLATFORM}" -t ${GHCR_REPO}:${GIT_TAG} .
elif [[ -n "${GIT_BRANCH}" ]]; then
  if [[ "${GIT_BRANCH}" == "master" ]]; then
    docker buildx build --progress plain --pull --push --platform "${DOCKER_BUILD_PLATFORM}" -t ${GHCR_REPO}:latest .
  else
    docker buildx build --progress plain --pull --push --platform "${DOCKER_BUILD_PLATFORM}" -t ${GHCR_REPO}:${GIT_BRANCH} .
  fi
else
  :
fi