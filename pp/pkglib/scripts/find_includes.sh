find . -type f | grep -v \.hg | grep -v \.git | grep -v \.bzr | grep -v egg-info | grep -v pyc | grep -v py~ | grep -v orig | grep -v log | grep -v EGG-INFO | grep -v PKG-INFO | sed 's/^.*\.//' | sort | uniq

