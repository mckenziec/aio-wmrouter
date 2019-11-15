import sys
import time
import os
import re

#from collectors.lib import utils

COLLECTION_INTERVAL = 10  # seconds

# Docs come from the Linux kernel's Documentation/iostats.txt
FIELDS_DISK = (
    "read_requests",        # Total number of reads completed successfully.
    "read_merged",          # Adjacent read requests merged in a single req.
    "read_sectors",         # Total number of sectors read successfully.
    "msec_read",            # Total number of ms spent by all reads.
    "write_requests",       # total number of writes completed successfully.
    "write_merged",         # Adjacent write requests merged in a single req.
    "write_sectors",        # total number of sectors written successfully.
    "msec_write",           # Total number of ms spent by all writes.
    "ios_in_progress",      # Number of actual I/O requests currently in flight.
    "msec_total",           # Amount of time during which ios_in_progress >= 1.
    "msec_weighted_total",  # Measure of recent I/O completion time and backlog.
    )

FIELDS_PART = ("read_issued",
               "read_sectors",
               "write_issued",
               "write_sectors",
              )

def read_uptime():
    try:
        f_uptime = open("/proc/uptime", "r")
        line = f_uptime.readline()

        return line.split(None)
    finally:
        f_uptime.close();

def get_system_hz():
    """Return system hz use SC_CLK_TCK."""
    ticks = os.sysconf(os.sysconf_names['SC_CLK_TCK'])

    if ticks == -1:
        return 100
    else:
        return ticks

def is_device(device_name, allow_virtual):
    """Test whether given name is a device or a partition, using sysfs."""
    device_name = re.sub('/', '!', device_name)

    if allow_virtual:
        devicename = "/sys/block/" + device_name + "/device"
    else:
        devicename = "/sys/block/" + device_name

    return (os.access(devicename, os.F_OK))

def main():
    """iostats main loop."""
    try:
        f_diskstats = open("/proc/diskstats", "r")
    except IOError as e:
        utils.err("error: can't open /proc/diskstats: %s" % e)
        return 13 # Ask tcollector to not respawn us

    HZ = get_system_hz()
    itv = 1.0
    uptime = read_uptime()
    #utils.drop_privileges()

    while True:
        f_diskstats.seek(0)
        ts = int(time.time())
        itv = read_uptime()[1]
        for line in f_diskstats:
            # maj, min, devicename, [list of stats, see above]
            values = line.split(None)
            # shortcut the deduper and just skip disks that
            # haven't done a single read.  This elimiates a bunch
            # of loopback, ramdisk, and cdrom devices but still
            # lets us report on the rare case that we actually use
            # a ramdisk.
            if values[3] == "0":
                continue

            if int(values[1]) % 16 == 0 and int(values[0]) > 1:
                metric = "iostat.disk."
            else:
                metric = "iostat.part."

            device = values[2]
            if len(values) == 14:
                # full stats line
                for i in range(11):
                    print(("%s%s %d %s dev=%s"
                           % (metric, FIELDS_DISK[i], ts, values[i+3],
                              device)))

                ret = is_device(device, 0)
                # if a device or a partition, calculate the svctm/await/util
                if ret:
                    stats = dict(list(zip(FIELDS_DISK, values[3:])))
                    nr_ios = float(stats.get("read_requests")) + float(stats.get("write_requests"))
                    tput = ((nr_ios) * float(HZ) / float(itv))
                    util = (float(stats.get("msec_total")) * float(HZ) / float(itv))
                    svctm = 0.0
                    await = 0.0

                    if tput:
                        svctm = util / tput

                    if nr_ios:
                        rd_ticks = stats.get("msec_read")
                        wr_ticks = stats.get("msec_write")
                        await = (float(rd_ticks) + float(wr_ticks)) / float(nr_ios)
                    print(("%s%s %d %.2f dev=%s" % (metric, "svctm", ts, svctm, device)))
                    print(("%s%s %d %.2f dev=%s" % (metric, "await", ts, await, device)))
                    print(("%s%s %d %.2f dev=%s" % (metric, "util", ts, float(util/1000.0), device)))

            elif len(values) == 7:
                # partial stats line
                for i in range(4):
                    print(("%s%s %d %s dev=%s"
                           % (metric, FIELDS_PART[i], ts, values[i+3],
                              device)))
            else:
                print("Cannot parse /proc/diskstats line: ", line, file=sys.stderr)
                continue

        sys.stdout.flush()
        time.sleep(COLLECTION_INTERVAL)



if __name__ == "__main__":
    main()

