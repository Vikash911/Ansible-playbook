pipeline{
    agent { 
    label 'mynode' 
    }
    environment{
    AWS_EC2_PRIVATE_KEY=credentials('private-key')
    }
    stages{
        stage("Pull code")
        {
            steps{
                git  'https://github.com/Vikash911/Ansible-playbook.git'
            }
        }
        stage("run ansible play"){
            steps{
               ansiblePlaybook credentialsId: 'private-key', disableHostKeyChecking: true, installation: 'Ansible', inventory: 'hosts.inv', playbook: 'docker_setup.yml' 
            }
        }
       
    }
}
