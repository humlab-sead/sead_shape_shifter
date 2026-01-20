#!/bin/bash
# Build script for SEAD Shape Shifter Docker image
# Usage: ./build.sh [OPTIONS]
#
# Build modes:
#   Local:  ./build.sh --local
#   Branch: ./build.sh --git-ref main (auto cache-bust)
#   Tag:    ./build.sh --git-ref v1.2.0 (no cache-bust)

set -e

RED='\e[31m'
GREEN='\e[32m'
YELLOW='\e[33m'
BLUE='\e[34m'
MAGENTA='\e[35m'
CYAN='\e[36m'
RESET='\e[0m'

# Script location
g_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
g_script_file="$(basename "${BASH_SOURCE[0]}")"

# Defaults
g_git_repo="https://github.com/humlab-sead/sead_shape_shifter.git"
g_git_ref=""
g_image_name="shape-shifter"
g_image_tag="latest"
g_containerfile="Dockerfile"
g_source="github"
g_no_cache=""
g_standalone=false
g_build_context=".."
g_user_uid=$(id -u sead 2>/dev/null || echo "1002")
g_user_gid=$(getent group www-data | cut -d: -f3 || echo "33")

function print_usage() {
    if [ "$1" != "" ]; then
        echo "error: $1"
    fi
    cat << EOF
Usage: $g_script_file [OPTIONS]

Build modes:
  --local               Build from local context (development)
  --git-ref REF         Build from GitHub branch or tag
  --standalone          Standalone mode: use current directory as context

Options:
  -t, --image-tag TAG   Docker image tag (default: auto-detect from git-ref)
  --image-name NAME     Docker image name (default: shape-shifter)
  --no-cache            Build without Docker cache
  --user-uid UID        Container user UID (default: sead user or 1002)
  --user-gid GID        Container user GID (default: www-data or 33)
  --git-repo URL        Git repository URL (default: official repo)
  --dockerfile PATH     Path to Dockerfile (default: Dockerfile)
  --context PATH        Build context directory (default: .. or . in standalone)
  -h, --help            Show this help message

Examples:
  # Build from local context (in repository)
  $g_script_file --local

  # Build from GitHub main branch (with cache invalidation)
  $g_script_file --git-ref main

  # Build from release tag
  $g_script_file --git-ref v1.2.0

  # Standalone mode (deployment server, current directory is context)
  $g_script_file --standalone --git-ref main

  # Standalone with custom Dockerfile location
  $g_script_file --standalone --git-ref main --dockerfile /path/to/Dockerfile

  # Build from branch with custom tag
  $g_script_file --git-ref develop --image-tag dev-latest

  # Build without cache
  $g_script_file --git-ref main --no-cache
EOF
    if [ "$1" != "" ]; then
        exit 64
    else
        exit 0
    fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --local)
            g_source="workdir"
            shift
            ;;
        --standalone)
            g_standalone=true
            g_build_context="."
            shift
            ;;
        --git-ref)
            g_git_ref="$2"
            g_source="github"
            shift 2
            ;;
        -t|--image-tag)
            g_image_tag="$2"
            shift 2
            ;;
        --image-name)
            g_image_name="$2"
            shift 2
            ;;
        --dockerfile)
            g_containerfile="$2"
            shift 2
            ;;
        --context)
            g_build_context="$2"
            shift 2
            ;;
        --no-cache)
            g_no_cache="--no-cache"
            shift
            ;;
        --user-uid)
            g_user_uid="$2"
            shift 2
            ;;
        --user-gid)
            g_user_gid="$2"
            shift 2
            ;;
        --git-repo)
            g_git_repo="$2"
            shift 2
            ;;
        -h|--help)
            print_usage
            ;;
        *)
            print_usage "unknown option $1"
            ;;
    esac
done

# Enforce standalone mode when source is github
if [ "$g_source" = "github" ]; then
    g_standalone=true
    echo "info: GitHub source enforces standalone mode"
fi

# Enforce script directory as context in standalone mode
if [ "$g_standalone" = true ] && [ "$g_build_context" != "$g_script_dir" ]; then
    g_build_context="$g_script_dir"
    echo "info: standalone mode enforces script directory as context: $g_script_dir"
fi

# Auto-detect image tag from git ref if not specified
if [ "$g_source" = "github" ] && [ "$g_image_tag" = "latest" ]; then
    if [[ "$g_git_ref" =~ ^v[0-9]+\.[0-9]+\.[0-9]+ ]]; then
        # Release tag: use tag as image tag
        g_image_tag="$g_git_ref"
    elif [ "$g_git_ref" = "main" ]; then
        g_image_tag="latest"
    else
        # Branch name: sanitize for Docker tag
        g_image_tag=$(echo "$g_git_ref" | sed 's/[^a-zA-Z0-9._-]/-/g')
    fi
fi

# Validate required arguments
if [ "$g_source" = "github" ] && [ -z "$g_git_ref" ]; then
    print_usage "git-ref is required when building from GitHub"
fi

# Determine if cache bust is needed (only for branches, not tags)
g_cache_bust="1"
g_additional_tags=()

if [ "$g_source" = "github" ]; then
    # Check if git-ref is a release tag (semver pattern)
    if [[ "$g_git_ref" =~ ^v[0-9]+\.[0-9]+\.[0-9]+ ]]; then
        echo "info: building from release tag $g_git_ref (no cache invalidation)"
        g_cache_bust="1"
        
        # Check if this tag equals main branch (for dual tagging)
        main_commit=$(git ls-remote "$g_git_repo" refs/heads/main 2>/dev/null | cut -f1)
        tag_commit=$(git ls-remote "$g_git_repo" "refs/tags/$g_git_ref" 2>/dev/null | cut -f1)
        
        if [ -n "$main_commit" ] && [ -n "$tag_commit" ] && [ "$main_commit" = "$tag_commit" ]; then
            echo "info: tag $g_git_ref equals main branch, adding 'latest' tag"
            g_additional_tags+=("$g_image_name:latest")
        fi
    else
        echo "info: building from branch $g_git_ref (with cache invalidation)"
        # Get latest commit SHA for cache busting
        g_cache_bust=$(git ls-remote "$g_git_repo" "refs/heads/$g_git_ref" 2>/dev/null | cut -f1)
        if [ -z "$g_cache_bust" ]; then
            echo "warning: could not fetch commit SHA, using timestamp for cache bust"
            g_cache_bust=$(date +%s)
        else
            echo "info: cache bust commit: ${g_cache_bust:0:8}"
            
            # If building main branch, check if latest tag points to same commit
            if [ "$g_git_ref" = "main" ]; then
                latest_tag=$(git ls-remote --tags --sort=-v:refname "$g_git_repo" 2>/dev/null | grep -v '\^{}' | grep -E 'refs/tags/v[0-9]+\.[0-9]+\.[0-9]+$' | head -1 | awk '{print $2}' | sed 's|refs/tags/||')
                
                if [ -n "$latest_tag" ]; then
                    tag_commit=$(git ls-remote "$g_git_repo" "refs/tags/$latest_tag" 2>/dev/null | cut -f1)
                    
                    if [ "$g_cache_bust" = "$tag_commit" ]; then
                        echo "info: main branch equals tag $latest_tag, adding version tag"
                        g_additional_tags+=("$g_image_name:$latest_tag")
                    fi
                fi
            fi
        fi
    fi
fi

echo ""
echo "============================================================"
echo "Build Configuration"
echo "============================================================"
echo "Mode:           $([ "$g_standalone" = true ] && echo "standalone" || echo "normal")"
echo "Source:         $g_source"
if [ "$g_source" = "github" ]; then
    echo "Repository:     $g_git_repo"
    echo "Git Ref:        $g_git_ref"
    echo "Cache Bust:     ${g_cache_bust:0:12}"
fi
echo "Image Name:     $g_image_name"
echo "Image Tag:      $g_image_tag"
if [ ${#g_additional_tags[@]} -gt 0 ]; then
    echo "Additional Tags: ${g_additional_tags[*]}"
fi
echo "Dockerfile:     $g_containerfile"
echo "Build Context:  $g_build_context"
echo "User UID:       $g_user_uid"
echo "User GID:       $g_user_gid"
echo "No Cache:       ${g_no_cache:-false}"
echo "============================================================"
echo ""

# Navigate to appropriate directory based on mode
if [ "$g_standalone" = true ]; then
    # Standalone mode: stay in current directory
    echo "Running in standalone mode (context: $PWD)"
else
    # Normal mode: navigate to docker directory
    cd "$g_script_dir"
fi

# Build command
build_args=(
    -f "$g_containerfile"
    --build-arg "SOURCE=$g_source"
    --build-arg "USER_UID=$g_user_uid"
    --build-arg "USER_GID=$g_user_gid"
    -t "$g_image_name:$g_image_tag"
)

if [ "$g_source" = "github" ]; then
    build_args+=(
        --build-arg "GIT_REPO=$g_git_repo"
        --build-arg "GIT_REF=$g_git_ref"
        --build-arg "CACHE_BUST=$g_cache_bust"
    )
fi

if [ -n "$g_no_cache" ]; then
    build_args+=("$g_no_cache")
fi

# Add context (parent directory for docker/Dockerfile)
build_args+=("$g_build_context")

# Execute build
echo "Executing: docker build ${build_args[*]}"
echo ""

docker build "${build_args[@]}"

echo -e ""
echo -e "${GREEN}============================================================${RESET}"
echo -e "${GREEN}✓ Build complete!${RESET}"
echo -e "${GREEN}============================================================${RESET}"
echo -e "${GREEN}Image:${RESET} $g_image_name:$g_image_tag"
echo -e ""
echo -e "${BLUE}To run the container:${RESET}"
echo -e "  cd $g_script_dir"
echo -e "  docker compose up -d"
echo -e ""
echo -e "${BLUE}Or standalone:${RESET}"
echo -e "  docker run -d -p 8012:8012 \\"
echo -e "    -v \$PWD/data/projects:/app/projects \\"
echo -e "    -v \$PWD/data/logs:/app/logs \\"
echo -e "    -v \$PWD/data/output:/app/output \\"
echo -e "    $g_image_name:$g_image_tag"
echo -e "${GREEN}============================================================${RESET}"
