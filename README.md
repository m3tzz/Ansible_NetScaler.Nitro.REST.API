######## Clone the repo in your search path ################
Once you have located your search path; browse to that directory and clone the netscaler-ansible repo:

cd /home/projects/
git clone git@github.com:m3tzz/NetScaler-NITRO-API.git


########### Install Dependencies ###########
All of the dependencies can be installed using the requirements.txt file that comes with the modules. Move to the new netscaler-ansible directory and use pip to install them.

pip install -r requirements.txt

############ How to run the playboox###############
### -t means the name of the tag you defined on your playbook #####
### -e means the name of the tag you defined on your playbook to call a device or more then one device ######
### --ask-vault-pass - provide the ansible-vault password to run playbook

#add
ansible-playbook -i inventories/ playbooks/play.yml -t add_vip_env1 -e ci_name=dc1-lb-env1 --ask-vault-pass

#rm
ansible-playbook -i inventories/ playbooks/play.yml -t rm_vip_env1 -e ci_name=dc1-lb-env1 --ask-vault-pass



Reference to build this code -->https://github.com/networktocode/netscaler-ansible
