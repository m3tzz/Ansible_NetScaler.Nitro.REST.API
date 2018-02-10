############ How to run the playboox###############
### -t means the name of the tag you defined on your playbook #####
### -e means the name of the tag you defined on your playbook to call a device or more then one device ######
### --ask-vault-pass - provide the ansible-vault password to run playbook

#add
ansible-playbook -i inventories/ playbooks/play.yml -t add_vip_env1 -e ci_name=dc1-lb-env1 --ask-vault-pass

#rm
ansible-playbook -i inventories/ playbooks/play.yml -t rm_vip_env1 -e ci_name=dc1-lb-env1 --ask-vault-pass
