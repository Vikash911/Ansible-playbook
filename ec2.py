#!/usr/bin/python3

'''
EC2 external inventory script
=================================
Generates inventory that Ansible can understand by making API request to
AWS EC2 using the Boto library.
NOTE: This script assumes Ansible is being executed where the environment
variables needed for Boto have already been set:
    export AWS_ACCESS_KEY_ID='AK123'
    export AWS_SECRET_ACCESS_KEY='abc123'
Optional region environment variable if region is 'auto'
This script also assumes that there is an ec2.ini file alongside it.  To specify a
different path to ec2.ini, define the EC2_INI_PATH environment variable:
    export EC2_INI_PATH=/path/to/my_ec2.ini
If you're using eucalyptus you need to set the above variables and
you need to define:
    export EC2_URL=http://hostname_of_your_cc:port/services/Eucalyptus
If you're using boto profiles (requires boto>=2.24.0) you can choose a profile
using the --boto-profile command line argument (e.g. ec2.py --boto-profile prod) or using
the AWS_PROFILE variable:
    AWS_PROFILE=prod ansible-playbook -i ec2.py myplaybook.yml
For more details, see: http://docs.pythonboto.org/en/latest/boto_config_tut.html
You can filter for specific EC2 instances by creating an environment variable
named EC2_INSTANCE_FILTERS, which has the same format as the instance_filters
entry documented in ec2.ini.  For example, to find all hosts whose name begins
with 'webserver', one might use:
    export EC2_INSTANCE_FILTERS='tag:Name=webserver*'
When run against a specific host, this script returns the following variables:
 - ec2_ami_launch_index
 - ec2_architecture
 - ec2_association
 - ec2_attachTime
 - ec2_attachment
 - ec2_attachmentId
 - ec2_block_devices
 - ec2_client_token
 - ec2_deleteOnTermination
 - ec2_description
 - ec2_deviceIndex
 - ec2_dns_name
 - ec2_eventsSet
 - ec2_group_name
 - ec2_hypervisor
 - ec2_id
 - ec2_image_id
 - ec2_instanceState
 - ec2_instance_type
 - ec2_ipOwnerId
 - ec2_ip_address
 - ec2_item
 - ec2_kernel
 - ec2_key_name
 - ec2_launch_time
 - ec2_monitored
 - ec2_monitoring
 - ec2_networkInterfaceId
 - ec2_ownerId
 - ec2_persistent
 - ec2_placement
 - ec2_platform
 - ec2_previous_state
 - ec2_private_dns_name
 - ec2_private_ip_address
 - ec2_publicIp
 - ec2_public_dns_name
 - ec2_ramdisk
 - ec2_reason
 - ec2_region
 - ec2_requester_id
 - ec2_root_device_name
 - ec2_root_device_type
 - ec2_security_group_ids
 - ec2_security_group_names
 - ec2_shutdown_state
 - ec2_sourceDestCheck
 - ec2_spot_instance_request_id
 - ec2_state
 - ec2_state_code
 - ec2_state_reason
 - ec2_status
 - ec2_subnet_id
 - ec2_tenancy
 - ec2_virtualization_type
 - ec2_vpc_id
These variables are pulled out of a boto.ec2.instance object. There is a lack of
consistency with variable spellings (camelCase and underscores) since this
just loops through all variables the object exposes. It is preferred to use the
ones with underscores when multiple exist.
In addition, if an instance has AWS tags associated with it, each tag is a new
variable named:
 - ec2_tag_[Key] = [Value]
Security groups are comma-separated in 'ec2_security_group_ids' and
'ec2_security_group_names'.
When destination_format and destination_format_tags are specified
the destination_format can be built from the instance tags and attributes.
The behavior will first check the user defined tags, then proceed to
check instance attributes, and finally if neither are found 'nil' will
be used instead.
'my_instance': {
    'region': 'us-east-1',             # attribute
    'availability_zone': 'us-east-1a', # attribute
    'private_dns_name': '172.31.0.1',  # attribute
    'ec2_tag_deployment': 'blue',      # tag
    'ec2_tag_clusterid': 'ansible',    # tag
    'ec2_tag_Name': 'webserver',       # tag
    ...
}
Inside of the ec2.ini file the following settings are specified:
...
destination_format: {0}-{1}-{2}-{3}
destination_format_tags: Name,clusterid,deployment,private_dns_name
...
These settings would produce a destination_format as the following:
'webserver-ansible-blue-172.31.0.1'
'''

# (c) 2012, Peter Sankauskas
#
# This file is part of Ansible,
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

######################################################################

import sys
import os
import argparse
import re
from time import time
from copy import deepcopy
from datetime import date, datetime
import boto
from boto import ec2
from boto import rds
from boto import elasticache
from boto import route53
from boto import sts

from ansible.module_utils import six
from ansible.module_utils import ec2 as ec2_utils
from ansible.module_utils.six.moves import configparser

HAS_BOTO3 = False
try:
    import boto3  # noqa

