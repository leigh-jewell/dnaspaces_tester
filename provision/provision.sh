#!/bin/bash
# Build and populate the VM: install and/or compile the necessary
# tools needed to run the minimal Flask application with Apache and mod_wsgi.
#
# This script is automatically run the *first time* you issue the command:
#
#    vagrant up
#

# Some convenience variables

APP_NAME=dnaspaces_tester
LOG_BASE="/var/log"
LOG_FILE="$LOG_BASE/$APP_NAME.log"
WWW_ROOT="/var/www/$APP_NAME"
SOURCE_ROOT="/vagrant"
SOURCE_PROVISION="/vagrant/provision"

# Temporary: Create and perm-fix log file
echo "*** Preparing log file ***"
sudo touch "$LOG_FILE"
sudo chmod 666 "$LOG_FILE"

echo "*** Installing prerequisite packages ***"

sudo apt-get update | tee $LOG_FILE 2>&1
sudo apt-get install -yq \
    python3-pip \
    apache2 \
    apache2-dev \
    libapache2-mod-wsgi-py3 | tee $LOG_FILE 2>&1

echo "*** Install Python modules ***"
if [ ! -f "$SOURCE_ROOT/requirements.txt" ]; then
  echo "ERROR: pip install requirements file missing." | tee "$LOG_FILE" 2>&1
  exit 1
else
  sudo -H pip3 install -r "$SOURCE_ROOT/requirements.txt" | tee "$LOG_FILE" 2>&1
fi

echo "*** Adding mod_wsgi config file to Apache modules ***"
sudo cp "$SOURCE_PROVISION/mod_wsgi.load" /etc/apache2/mods-available | tee "$LOG_FILE" 2>&1
if [ ! -f /etc/apache2/mods-available/mod_wsgi.load ]; then
  echo "ERROR: file mod_wsgi.load not copied to /etc/apache2/mods-available" | tee "$LOG_FILE" 2>&1
  exit 1
fi

echo "*** Creating wwww-data dir for log files ***"
sudo mkdir /home/www-data | tee $LOG_FILE 2>&1
sudo chown -R www-data:www-data /home/www-data | tee "$LOG_FILE" 2>&1

echo "*** Creating virtual host site configuration for Apache ***"
sudo cp -f "$SOURCE_PROVISION/apache_site.conf" "/etc/apache2/sites-available/$APP_NAME.conf" | tee "$LOG_FILE" 2>&1
if [ ! -f "/etc/apache2/sites-available/$APP_NAME.conf" ]; then
  echo "ERROR: unable to copy file to /etc/apache2/sites-available/$APP_NAME.conf" | tee "$LOG_FILE" 2>&1
  exit 1
fi

sudo a2ensite $APP_NAME.conf | tee "$LOG_FILE" 2>&1

echo "*** Removing default sites ***"
sudo a2dissite default-ssl.conf | tee "$LOG_FILE" 2>&1
sudo a2dissite 000-default.conf | tee "$LOG_FILE" 2>&1

echo "*** Creating self signed certificate ***"
if ! sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
 -keyout /etc/ssl/private/apache-selfsigned.key \
 -out /etc/ssl/certs/apache-selfsigned.crt \
 -subj "/C=AU/ST=NSW/L=Sydney/O=Cisco/OU=Cisco/CN=dnas_step_tracker.com" >> "$LOG_FILE" 2>&1; then
  echo "ERROR: self-signed certificate /etc/ssl/private/apache-selfsigned.key not created." | tee "$LOG_FILE" 2>&1
  exit 1
fi

echo "*** Create a strong Diffie-Hellman group ****"
if ! sudo openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048 | tee "$LOG_FILE" 2>&1; then
  echo "ERROR: Diffie-Hellman not created /etc/ssl/certs/dhparam.pem." | tee "$LOG_FILE" 2>&1
  exit 1
fi

echo "*** Copy SSL configuration for Apache2 ***"
sudo cp "$SOURCE_PROVISION/apache_ssl_params.conf" /etc/apache2/conf-available/apache_ssl_params.conf | tee "$LOG_FILE" 2>&1
if [ ! -f "/etc/apache2/conf-available/apache_ssl_params.conf" ]; then
  echo "ERROR: Apache SSL /etc/apache2/conf-available/apache_ssl_params.conf not copied." | tee "$LOG_FILE" 2>&1
  exit 1
fi

echo "*** Enable the SSL changes in Apache ***"
sudo a2enmod ssl | tee $LOG_FILE 2>&1
sudo a2enmod headers | tee $LOG_FILE 2>&1
sudo a2enconf apache_ssl_params | tee "$LOG_FILE" 2>&1

echo "*** Restarting Apache to inculde changes ***"
sudo systemctl restart apache2 | tee "$LOG_FILE" 2>&1

echo "*** Checking Apache site enabled ***"
if a2query -s | grep -q $APP_NAME; then
   echo "*** Success : Apache site $APP_NAME enabled ***"
else
  echo "ERROR: Apache site $APP_NAME NOT enabled"
  exit 1
fi

echo "*** Checking Apache modules ***"
modules="ssl headers wsgi"
for MODULE in $modules; do
  if a2query -m | grep -q $MODULE; then
     echo "Apache $MODULE enabled" | tee "$LOG_FILE" 2>&1
  else
    echo "*** ERROR ***: Apache $MODULE NOT enabled" | tee "$LOG_FILE" 2>&1
  fi
done
echo "*** Finished provisioning ***"

