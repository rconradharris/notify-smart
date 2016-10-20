# Place this in your irssi scripts directory ~/.irssi/scripts and load it using:
#   /load reply.pl
use strict;
use File::Basename;
use vars qw($VERSION %IRSSI);

use Irssi;
$VERSION = '0.0.1';
%IRSSI = (
    authors     => 'Rick Harris',
    contact     => 'rconradharris@gmail.com',
    name        => 'reply',
    description => 'Reply to IRC messages programmatically',
    url         => '<add this>',
    license     => 'GNU General Public License',
    changed     => '$Date: 2016-09-27 12:00:00 +0100 (Tue, 27 Sep 2016) $'
);

sub poller {
    my $server = Irssi::server_find_tag("rackspace");
    foreach my $path (glob("~/.irssi/reply-data/*")) {
        # Determine if file is recent enough
        my $age = time - basename($path);
        if ($age < 30) {
            # Read file and send IRC message to target
            open(my $file, '<', $path);
            my $contents = <$file>;
            (my $target, my $reply) = split /[:\s]+/, $contents, 2;
            $server->command('msg ' . $target . ' ' . $reply);
        }
        unlink $path;
    }
}

Irssi::timeout_add(1000, "poller", "");
