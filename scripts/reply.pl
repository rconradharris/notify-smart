use strict;
use File::Basename;
use vars qw($SERVER $ROTATE $VERSION %IRSSI);

use Irssi;
$SERVER = 'rackspace';
$ROTATE = 25;
$VERSION = '0.0.3';
%IRSSI = (
	authors     => 'Rick Harris',
	contact     => 'rconradharris@gmail.com',
	name        => 'reply',
	description => 'Reply to IRC messages programmatically',
	url         => '<add this>',
	license     => 'GNU General Public License',
	changed     => '$Date: 2016-09-27 12:00:00 +0100 (Tue, 27 Sep 2016) $'
);

sub reply_poller {
    foreach my $path (glob("~/.irssi/reply-data/*")) {
        # Determine if file is recent enough
        my $age = time - basename($path);
        if ($age < 30) {
            # Read file and send IRC message to target
            open(my $file, '<', $path);
            (my $target, my $reply) = split /[:\s]+/, <$file>, 2;
            Irssi::server_find_tag($SERVER)->command('msg ' . $target . ' ' . $reply);
            close($file);
        }
        unlink $path;
    }
}

sub append_file {
	my ($filename, $text) = @_;
    my $path = "$ENV{HOME}/.irssi/".$filename;
    mkdir(dirname($path));
    open(my $file, ">>".$path);
    print($file $text . "\n");
    close($file);
    # Rotate file
    system("tail -n$ROTATE $path > $path.tmp && mv $path.tmp $path");
}

sub log_transcript {
    my ($dest, $text, $stripped) = @_;
    if (($dest->{level} & MSGLEVEL_PUBLIC) || ($dest->{level} & MSGLEVEL_MSGS)) {
        my $filename = "transcripts/" . $dest->{target};
        append_file($filename, $stripped);
    }
}


Irssi::signal_add_last("print text", "log_transcript");
Irssi::timeout_add(250, "reply_poller", "");
