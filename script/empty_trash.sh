#
# look at scriptCB() function in MovieSelection.py (~ line 460) for a list of available SP_* env variables
#
# script input params:
#  $1 = current path selection
#  $2 = filename of current service selection (with path)

[ ! -e $SP_TRASH/proc ] && rm -f $SP_TRASH/*
