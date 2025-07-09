#!/bin/bash
# Remove default nginx configurations that might conflict
rm -f /etc/nginx/sites-enabled/default
rm -f /etc/nginx/sites-available/default
rm -f /etc/nginx/conf.d/default.conf.bak
echo "Default configurations removed"
