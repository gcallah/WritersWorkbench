#!/bin/sh
echo "Setting up a new PythonAnywhere server."

bcore="backendcore"
# so we can keep the name the same in config file:
main_repo="main-repo"

when_done="When you have done that step press any key to continue."

echo "Getting account name."
account=$(basename "$PWD")
echo "Account name: $account; that should also be the name of the repo!"

echo "Setting up ssh for the repo (https://help.pythonanywhere.com/pages/ExternalVCS/)"
echo "Name your new key $main_repo"
ssh-keygen
# In case the ssh demon is not running, we start it.
eval $(ssh-agent -s)
ssh-add ~/.ssh/$main_repo
# See the github documentation at https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent#generating-a-new-ssh-key
echo "Add the following to the deploy keys section of your GitHub repo:"
cat ~/.ssh/$main_repo.pub

echo "$when_done"
read any_key

echo "Cloning the repo with ssh."
git clone git@app.github.com:AthenaKouKou/$account.git

echo "Generating an ssh key for $bcore."
echo "Name your new key $bcore"
ssh-keygen
ssh-add ~/.ssh/$bcore
echo "Add the following to the deploy keys section of the BackEndCore GitHub repo:"
cat ~/.ssh/$bcore.pub

echo "$when_done"
read any_key

echo "Adding keys to ssh config file."
cat >~/.ssh/config << EOL
# DMM backend repo
Host app.github.com
HostName github.com
PreferredAuthentications publickey
IdentityFile ~/.ssh/$main_repo

# backend core repo
Host github.com
HostName github.com
PreferredAuthentications publickey
IdentityFile ~/.ssh/$bcore
EOL

echo "Installing the PA command line tools."
pip install pythonanywhere

echo "Setting up a virtual env. (https://help.pythonanywhere.com/pages/Virtualenvs/)"
mkvirtualenv $account --python=/usr/bin/python3.10
echo "Entering the virtual env."
workon $account

echo "Installing Python packages."
pip install -r requirements.txt

echo "Generate an API token in the Account tab of PA."
echo "Enter the API token here:"
read api_token
echo "export API_TOKEN=$api_token" >> .bashrc

# Let's automate these steps:
# Create the WSGI file, probably by copying an existing PA account's file and modifying it.
# Modify `deploy.sh` and `rebuild.sh` appropriately.

echo "Put the password for this account in your GitHub Action secrets."
