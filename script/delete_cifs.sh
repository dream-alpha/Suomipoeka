find $SP_HOME -name cifs* | grep -v '.ts' | while read fn; do rm -f $fn; done
