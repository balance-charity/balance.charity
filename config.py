#!/bin/env python3
import os

srvname     = 'kdlp.underground.software'
refresh     = 0

appname     = 'balance'
version     = '0.1'
source      = 'https://github.com/underground-software/balance.charity'

radius_port = '9098'


orbit_root   = '/home/joel/BALANCE/thebalancejerusalem.org'

# read these documents from a filesystem path
dataroot    = f'{orbit_root}/docs'

logo    = f'{dataroot}/logo.png'
style   = f'{dataroot}/style.css'


title       = 'The Balance'
nav_buttons = [
    ('/home', 'Home'     ),
    ('/about', 'About Us' ),
    ('/testimonials', 'Testimonials'),
    ('/faq', 'FAQ'),
    ('/join', 'Get Involved')]
