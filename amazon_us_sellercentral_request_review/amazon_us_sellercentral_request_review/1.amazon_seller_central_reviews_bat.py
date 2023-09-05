#!/usr/bin/env python


#.replace(' ','\ ')

import os
import platform
import subprocess
import sys

p = platform.system()

if p == 'Darwin': # darwin = mac os

    absolute_path = os.path.abspath(__file__).replace(' ','\ ')
    print("Directory Path: " + os.path.dirname(absolute_path))

else: # this is windows

    absolute_path = os.path.abspath(__file__)
    print("Directory Path: " + os.path.dirname(absolute_path))


os.system("scrapy crawl sellercentral")
