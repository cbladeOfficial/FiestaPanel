#!/usr/bin/env bash
# ==============================================================================
# FiestaPanel - Push to GitHub Helper
# ==============================================================================
set -e

REPO_DIR="/home/ubuntu/fiesta-portal"
cd "$REPO_DIR"

COLOR_CYAN="\033[1;36m"
COLOR_GREEN="\033[1;32m"
COLOR_YELLOW="\033[1;33m"
COLOR_RESET="\033[0m"

echo -e "${COLOR_CYAN}=== FiestaPanel GitHub Publisher ===${COLOR_RESET}"
echo "Current branch: $(git branch --show-current)"
echo "Commits ready to push:"
git log -2 --oneline
echo ""

echo -e "${COLOR_YELLOW}Choose authentication method:${COLOR_RESET}"
echo "1) Web Browser login (GitHub CLI: gh auth login -w)"
echo "2) GitHub Personal Access Token (PAT)"
echo "3) SSH Key (git@github.com:...)"
echo ""
read -rp "Option [1/2/3]: " AUTH_OPT

case "$AUTH_OPT" in
    1)
        echo -e "${COLOR_CYAN}Starting GitHub CLI Web Login...${COLOR_RESET}"
        gh auth login -h github.com -p https -w
        echo -e "${COLOR_GREEN}Authentication complete! Creating repository and pushing...${COLOR_RESET}"
        read -rp "Enter repository name [fiestapanel]: " REPO_NAME
        REPO_NAME="${REPO_NAME:-fiestapanel}"
        gh repo create "$REPO_NAME" --public --source=. --remote=origin --push || git push -u origin main
        echo -e "${COLOR_GREEN}Successfully pushed to GitHub!${COLOR_RESET}"
        ;;
    2)
        read -rp "Enter your GitHub username: " GH_USER
        read -rsp "Enter your GitHub Personal Access Token (with 'repo' scope): " GH_TOKEN
        echo ""
        read -rp "Enter repository name [fiestapanel]: " REPO_NAME
        REPO_NAME="${REPO_NAME:-fiestapanel}"
        git remote remove origin 2>/dev/null || true
        git remote add origin "https://${GH_USER}:${GH_TOKEN}@github.com/${GH_USER}/${REPO_NAME}.git"
        git push -u origin main
        echo -e "${COLOR_GREEN}Successfully pushed to https://github.com/${GH_USER}/${REPO_NAME}!${COLOR_RESET}"
        ;;
    3)
        read -rp "Enter your GitHub SSH repository URL (e.g. git@github.com:username/fiestapanel.git): " SSH_URL
        git remote remove origin 2>/dev/null || true
        git remote add origin "$SSH_URL"
        git push -u origin main
        echo -e "${COLOR_GREEN}Successfully pushed to $SSH_URL!${COLOR_RESET}"
        ;;
    *)
        echo "Invalid option."
        exit 1
        ;;
esac
