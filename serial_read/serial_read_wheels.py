#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright © 2018 Clément Bourguignon, The Storch Lab, McGill
# Distributed under terms of the MIT license.

import click
import serial
import time
import struct

@click.group()
def cli():
    """
    Read Arduino's serial messages and decompress the subsequent files.
    """

@cli.command()
@click.option('--port','-p',default="/dev/ttyACM0",help="The port of the Arduino")
@click.option('--baudrate','-b',default=9600,help="Baudrate for the serial comm")
@click.option('--n_wheels','-n',default=10,help="Number of wheels in serial line")
@click.option('--template','-t',default="wheel_n_",help="Initial part of the output name. Numbers get added at the end.\nExample: 'pir_n_'--> pir_n_04")
@click.option('--binsize','-s',default=60,help="Size of bin window in seconds")
@click.option('--destructive','-d',default=False,help="Overwrite old files")
def encode(port,baudrate,n_wheels,template,binsize,destructive):
    """
        Open Arduino's serial port and encode incoming message to files
        with a timestamp.
    """

    template_filename=template+"%02d"

    if destructive:
        for n in range(n_pir):
            with open(template_filename%(n+1),'wb') as f:
                f.write()

    try:
        click.echo("[ ] Serial port")
        ser = serial.Serial(port, baudrate)
        tt1 = time.localtime()[:6]
        click.echo("Start time: %04d-%02d-%02d %02d:%02d:%02d."%tt1)
        click.echo("\r[*] Serial port")
        click.echo("[*] Reading stream")
        # Wait 1.5 second for garbage to get out serial
        time.sleep(1.5)
    except serial.SerialException:
        click.echo("\r[-] Serial connection error.")
        return

    while True:
        try:
            # Get values from serial
            in_serial = ser.readline()
            if in_serial == b'':
                continue
            cleaned_serial = [int(x, 10) for x in in_serial.strip().split(b'\t')]
            # Write values to file
            timestamp = int(time.time())
            for n in range(len(cleaned_serial)):
                with open(template_filename%(n+1), 'ab') as f:
                    rot = cleaned_serial[n]
                    out_string=struct.pack('=II', timestamp,rot)
                    f.write(out_string)
            click.echo([time.strftime("%H:%M:%S", time.localtime())] + cleaned_serial)
        except (KeyboardInterrupt,SystemExit):
            t_end=time.localtime(time.time())[:6]
            click.echo("\n[C] Exiting")
            click.echo("[-] Serial connection ended at %04d-%02d-%02d %02d-%02d-%02d"%t_end)
            return
        except ValueError:
            continue


@cli.command()
@click.option('--n_wheels','-n',default=10,help="Number of PIRs in serial line")
@click.option('--template','-t',default="pir_n_",help="Initial part of the output name (template format)")
@click.option('--localtime','-l',default=0,help="Output timestamps in local time rather than unix epoch time.\nWARNING: be careful with daylight saving time!")
@click.option('--draw','-d',default=0,help="set to 1 to display actogram after decoding")
@click.option('--bin_display','-b',default=0,help="set binsize for actogram display in minutes")
def decode(n_pir,template,localtime,draw,display_bin):
    """
        Decode files that were created with Arduino's serial messages.
    """

    template_filename = template + "%02d"

    for n in range(n_wheels):
        decode_in_file = template_filename%(n+1)
        decode_out_file = decode_in_file+"_parsed.txt"
        click.echo('Working on file: %s'%decode_out_file)
        buff_size = 8
        try:
            with open(decode_in_file, 'rb') as i: #
                with open(decode_out_file, 'w') as o:
                    #Header
                    o.write('time,Status\n')
                    while True:
                        anteroom = i.read(buff_size)
                        if anteroom == b'':
                            break
                        anteroom_tuple = struct.unpack('=II', anteroom)
                        timestamp = anteroom_tuple[0]
                        status = anteroom_tuple[1]
                        if localtime:
                            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
                            o.write('%s,%i\n'%(timestamp,status))
                        else:
                            o.write('%i,%i\n'%(timestamp,status))

        except FileNotFoundError:
            print('File not found')
            continue

    if draw:
        actogram(template_filename, n_wheels, bin_display)


def actogram(template_filename, n_wheels, bin_display):
    from datetime import time as ti
    import pandas as pd
    import matplotlib.pyplot as plt
    import math

    template_filename = template_filename + "_parsed.txt"

    nlin = round(math.sqrt(n_wheels))
    ncol = math.ceil(math.sqrt(n_wheels))
    fig, ax = plt.subplots(nlin,ncol,sharex='all',sharey='all')

    for n in range(n_wheels):
        ls_ts=list()
        ls_stat = list()
        PIR_dataframe = None
        try:
            with open(template_filename%(n+1),'r') as f:
                f.readline()
                while True:
                    tmp=f.readline()
                    if tmp=='':
                        break
                    tmp=[int(x) for x in tmp.strip().split(',')]
                    ls_ts.append(datetime.fromtimestamp(tmp[0]))
                    ls_stat.append(tmp[1])
                f.close()
                PIR_dataframe = pd.DataFrame({'Status':ls_stat}, index=ls_ts)

        except ValueError:
            # The date is already converted
            PIR_dataframe = pd.read_csv(template_filename%(n+1),index_col='time', parse_dates=True)

        binsize = (PIR_dataframe.index[1]-PIR_dataframe.index[0]).seconds/3600

        # resample data in x-minute bins to avoid heavy figures
        if bin_display:
            print('binning data in %i-minute bins'%bin_display)
            PIR_dataframe = PIR_dataframe.resample('%iT'%bin_display).mean()
            binsize = (PIR_dataframe.index[1]-PIR_dataframe.index[0]).seconds/3600

        days_array = pd.date_range(PIR_dataframe.index[0].date(), PIR_dataframe.index[-1].date()+timedelta(days=1))

        n_days=len(days_array)-1
        k=n_days

        lin = math.floor((n)/ncol)
        col = (n)%ncol

        for i in range(n_days):
            idx = numpy.logical_and(PIR_dataframe.index < datetime.combine(days_array[i+1], ti(0,0,0)),
                                    PIR_dataframe.index >= datetime.combine(days_array[i], ti(0,0,0)))
            x = PIR_dataframe.index[idx]
            x = x.hour+x.minute/60+x.second/3600
            y = PIR_dataframe.Status.iloc[idx] * 0.9
            # y = numpy.ones((len(x),)) * (k-1)
            # u = numpy.zeros((len(x),))
            # v = PIR_dataframe.Status.iloc[idx]
            if nlin>1:
                # ax[lin,col].quiver(x, y, u, v,
                # headwidth=0, angles='xy', scale_units='xy', scale=1)
                # ax[lin,col].quiver(x+24, y+1, u, v,
                # headwidth=0, angles='xy', scale_units='xy', scale=1)
                # ax[lin,col].plot([0,48], [k-1,k-1], color='black')
                ax[lin,col].fill_between(x, k-1, y+k-1, where=y+k>k, color='black', edgecolor='none')
                ax[lin,col].fill_between(x+24, k, y+k, where=y+k>k,  color='black', edgecolor='none')
                ax[lin,col].plot([0,48], [k-1,k-1], color='black')
            else:
                # ax[lin].quiver(x, y, u, v,
                # headwidth=0, angles='xy', scale_units='xy', scale=1)
                # ax[lin].quiver(x+24, y+1, u, v,
                # headwidth=0, angles='xy', scale_units='xy', scale=1)
                # ax[lin].plot([0,48], [k-1,k-1], color='black')
                ax[col].fill_between(x, k-1, y+k-1, where=y+k>k, color='black', edgecolor='none')
                ax[col].fill_between(x+24, k, y+k, where=y+k>k,  color='black', edgecolor='none')
                ax[col].plot([0,48], [k-1,k-1], color='black')
            k-=1

        if nlin>1:
            ax[lin,col].set_title(template_filename%(n+1))
        else:
            ax[col].set_title(template_filename%(n+1))

    plt.xticks(range(0, 48, 6),
               ['00:00', '06:00', '12:00', '18:00', '00:00', '06:00', '12:00', '18:00'])
    plt.yticks(numpy.arange(0.5,n_days,1), reversed(days_array[0:-1].strftime("%a %d-%m")))
    plt.ylim(ymax=n_days)
    plt.xlim(xmin=0,xmax=48)
    plt.show()
    plt.savefig(template_filename + '.png')
