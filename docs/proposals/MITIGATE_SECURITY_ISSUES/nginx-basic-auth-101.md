# Nginx Basic Authentication: 101

This guide shows how to manage users for sites protected with nginx HTTP Basic Authentication.

## How it works

The nginx directive below identifies the password file used by a site:

```nginx
auth_basic "Restricted Area";
auth_basic_user_file /etc/nginx/.htpasswd;
```

Sites that reference the **same password file** share the same users and passwords. Basic authentication does not automatically apply to every nginx site; it applies only where `auth_basic` is configured or inherited.

## Install the user-management command

On Ubuntu or Debian:

```bash
sudo apt install apache2-utils
```

This installs `htpasswd`.

## Add users to an existing password file

```bash
sudo htpasswd /etc/nginx/.htpasswd alice
sudo htpasswd /etc/nginx/.htpasswd bob
```

You will be prompted for each password.

> Do not use `-c` when the file already exists: it recreates the file and removes the existing users.

## Create a site-specific user list

A separate password file per site is usually clearest:

```bash
sudo install -d -m 750 -o root -g www-data /etc/nginx/htpasswd
sudo htpasswd -c /etc/nginx/htpasswd/shape-shifter alice
sudo htpasswd /etc/nginx/htpasswd/shape-shifter bob
sudo chown root:www-data /etc/nginx/htpasswd/shape-shifter
sudo chmod 640 /etc/nginx/htpasswd/shape-shifter
```

Configure the site to use it:

```nginx
server {
    server_name shape-shifter.sead.se;

    auth_basic "Shape Shifter";
    auth_basic_user_file /etc/nginx/htpasswd/shape-shifter;

    # ...
}
```

Another site can use another file, for example:

```nginx
auth_basic_user_file /etc/nginx/htpasswd/another-site;
```

## Manage users

List usernames without exposing password hashes:

```bash
sudo cut -d: -f1 /etc/nginx/htpasswd/shape-shifter
```

Change a user's password:

```bash
sudo htpasswd /etc/nginx/htpasswd/shape-shifter alice
```

Remove a user:

```bash
sudo htpasswd -D /etc/nginx/htpasswd/shape-shifter alice
```

## Validate changes

After changing nginx configuration:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Editing only the password file normally requires no nginx reload.

## Passing the username to the application

This proxy header forwards the authenticated username:

```nginx
proxy_set_header X-Authenticated-User $remote_user;
```

The application should trust this header only from nginx. Keep the upstream bound to localhost, for example `127.0.0.1:8012`, so external clients cannot bypass authentication and forge the header.

## Quick recommendation

- Use `/etc/nginx/htpasswd/<site-name>` for each site's credentials.
- Give the file `root:www-data` ownership and mode `640`.
- Reserve one shared file only for sites that intentionally share an account list.
