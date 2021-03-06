#!/usr/bin/perl

use Env;
use DBI;
use lib "scripts";
require image_sharing;

sub send_DICOM {
 my ($ae, $host, $port) = @_;

 @image_sets = (
	".5001.1\tWalters^Edwin\tA-5001-04-1\tA-5001-04-1F",
	".5001.2\tOsgood^Walter\tA-5001-04-2\tA-5001-04-2F",
	".5001.3\tDewalt^Kim\tA-5001-04-3\tA-5001-04-3F",
	".5001.4\tDemarco^K\tA-5001-04-4\tA-5001-04-4F",
	".5001.5\tDemarco^K\tA-5001-04-4\tA-5001-04-5F",
	".5001.14\tO'\\''Hare^Butch\tA-5001-14-1\tA-5001-14-1F",
	".5001.14\tTravers-Marr^Ida\tA-5001-14-2\tA-5001-14-2F"
 );

 foreach $im(@image_sets) {
  my($uidSuffix, $name, $id, $acc) = split("\t", $im);
  $uidSuffix = $uidSuffix . image_sharing::generate_date_time();
  $uidSuffix = $uidSuffix . ":" . $uidSuffix . ":" . $uidSuffix;
  my $inputFolder = "$MESA_TARGET/storage/modality/MR/MR1/MR1S2";
  image_sharing::cstore($inputFolder, $ae, $host, $port, $name, $id, $acc, $uidSuffix);
 }

}


## Main starts here
 image_sharing::check_environment();
 image_sharing::clear_db("rsnadb");
 
 my $ae = "DCM4CHEE";
 my $host = "10.242.100.66";
 my $port = "11112";
 die "Set host to real value, not $host.\nSearch for $host in this script and repair it.\n  " if ($host eq "10.242.100.999");


 my $verbose = "";
 $verbose = "1" if (scalar(@ARGV) > 0);
 chdir("data/A-5001");
 print `perl A-5001.pl $verbose`;
 die if $?;
 chdir("../..");

 @hl7_msgs = (
	"A-5001-04-1-orm", "A-5001-04-2-orm",
	"A-5001-04-3-orm", "A-5001-04-4-orm",
	"A-5001-04-5-orm", "A-5001-14-1-orm",
	"A-5001-14-2-orm",
	"A-5001-04-1-oru", "A-5001-04-2-oru",
	"A-5001-04-3-oru", "A-5001-04-4-oru",
	"A-5001-04-5-oru", "A-5001-14-1-oru",
	"A-5001-14-2-oru",
 );
 foreach $msg(@hl7_msgs) {
  print "$msg\n";
  my $x = "$MESA_TARGET/bin/send_hl7 localhost 20000 data/A-5001/$msg" . ".hl7";
  print "$x\n";
  print `$x`;
  die "Could not send HL7 message to localhost" if $?;
 }

 send_DICOM($ae, $host, $port);

 my $y =
 "The automated part of test A-5001-04 is complete.\n" .
 " The database is loaded with records. The next part of\n" .
 " the test process consists of manual steps described\n" .
 " in the test procedure.\n";

 print $y;
