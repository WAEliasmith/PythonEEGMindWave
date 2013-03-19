import matplotlib
from pylab import *
from numpy import mean, zeros, floor
from numpy.fft import fft
import time
import serial
import smooth
from pygame import mixer
from pygame import sndarray
from EEGPlots import *
import pdb #for debugging; pdb.set_trace()
from parser import Parser

plotLength = 1000 #Amount of data to show
sampleTime=1.0/512 #seconds 

def startEEG(runTime, averages=[], blinks=False, music=False, smoothness=0, sampling=400):
    #runTime: the number of seconds to run for
    #averages: provides times to compute average spectra between
    #blinks: whether or not to detect blinks
    #music: whether or not to record to a file to play as music
    #smoothness: needs to be zero for no smoothing, otherwise an odd integer
    #sampling: 400 gives a rapid plot update, but delay between actions and effects
    #		   1000 gives jerky plot update, but little delay between actions and effects (for blinks)
    
    p = Parser(sampling) #start the parser to give data from the MindWave
    
#### Set up all the graphs for plotting
    ion() #Turn interactive plots on
    matplotlib.rc('lines', linewidth=1)
    figure(figsize=(10,8))
    gs = GridSpec(1, 2, width_ratios=[4, 1])  #Set relative size of subplots
    
    x = arange(0,plotLength) # x-axis
    y = [0.0]*len(x) #initialize y to all zeros

    ax0 = subplot(gs[0]) #Set up time plots
    line = ax0.plot(x*sampleTime,y,'r')[0] #Set the EEG plot up
    axis('tight')
    ylim((-4,4)) #ensure the plot scale is correct

    if blinks:
        line2, = plot(x*sampleTime,y,"g")  #Set up the smoothed plot
        dots, = plot(1,1,"g*")  #Set up to plot detected blinks
    xlabel('Time (s)')
    ylabel('Brain Signal')

    ax1 = subplot(gs[1]) #Set up spectrum plot
    bar = barh(range(50),[.2]*50)
    ylabel('Frequency (Hz)')
    xlabel('Power')

#### Set up variables for the main loop    
    t1=time.time()
    t2=0
    i=0
    blinkCount = 0
    blinker = []
    spectra = []
    avgSpectra = []
    avgSpectraAll = []
    stopAverage = False
    if not averages:
        stopAverage = True

#### Main loop
    if music:  #Start recording data to a file for brain music
        p.start_raw_recording("brain_music.raw")
    while (t2-t1)<runTime:
        p.update()
        if not p.sending_data:
            print "Hey! The MindWave's not connected!"

        length = len(p.raw_values)
        if length > plotLength:
            y = p.raw_values[-1000:]
        elif len(p.raw_values)!= 0: 
                y[-length:]=p.raw_values
        
        y = array(y)
        
#### Blink detection ####
        if blinks:
            blinker = smooth.smooth(y,151)
            blinker = blinker[75:-75]
            ind = where(abs(y-blinker) > 15000)[0]

            realBlink = []
            i=0
            while i < len(ind):
                blinkInd = where(ind > (ind[i]+40))[0]
                if blinkInd.any():
                    if blinkInd[0] > i+20:
                    	blinkInd[0]
                        realBlink.append(ind[blinkInd[0]])
                        blinkCount += 1
                        i += 60 #Don't test for a while
                i+=1
            line2.set_ydata(list(blinker/10000.0))
            dots.set_xdata(list(array(realBlink)*sampleTime))
            dots.set_ydata([3]*len(realBlink))

#### Figure out the spectrum            
        relative_spectrum, abs_spectrum = FFT(p.raw_values, range(51), 512)           
    	spectra.append(array(relative_spectrum))
        if len(spectra)>30:
                spectra.pop(0)
        spectrum = mean(array(spectra),axis=0) #running avg spectrum
        for b, h in zip(bar, spectrum): #update frequency plot
            b.set_width(h)#/20000000.0)
            
###Keep the average spectrum if needed (for music)
        if not stopAverage:
            if averages[i] >= (t2-t1):
                avgSpectra.append(array(relative_spectrum))
            else:
                i += 1
                if i > len(averages)-1:
                    stopAverage=True
                avgSpectraAll.append(mean(array(avgSpectra),axis=0))
                avgSpectra = []
                
#### Smooth the raw data if desired                
        if smoothness>0:
            y=smooth.smooth(y,smoothness)
            y=y[(smoothness-1)/2:-(smoothness-1)/2]

#### Update the time plot and finish the loop                    
        line.set_ydata(list(y/10000.0)) #Update the time plot
        
        draw() #Redraw the plot
    
        t2=time.time()
        
    if music:  #Stop recording to the file for brain music
        p.stop_raw_recording()
    
    return avgSpectraAll, blinkCount/8

#### Function to compute the Fast Fourier Transform
def FFT(X, Band, SamplingRate):
    C = fft(X)  #Do the FFT to the input signal
    C = abs(C)  #Get the power
    Power = zeros(len(Band)-1);
    for Freq_Index in xrange(0,len(Band)-1):
        Freq = float(Band[Freq_Index]) 
        Next_Freq = float(Band[Freq_Index+1])
        Power[Freq_Index] = sum(C[floor(Freq/SamplingRate*len(X)):
                                     floor(Next_Freq/SamplingRate*len(X))]) #Sum power over the band
    Power_Ratio = Power/sum(Power)  #Compute the relative power for each freq
    return Power_Ratio, Power

#################
# Experiment 1: Blink detection
################
def expt1():
    print '---------------------------'
    print 'Experiment 1: Blink detection\n'
    raw_input('Hit enter to start. I will detect your blinks for 30s (no talking or swallowing!).')
    data, blinkCount = startEEG(30, blinks=True, sampling = 1000)  
    print 'I detected %s blinks' % blinkCount
    raw_input('Hit enter to continue...')
    print('\n\n')

#################
# Experiment 2: Songs
################    
def expt2():
    print '-------------------'
    print 'Experiment 2: Songs\n'
    raw_input('Put in the earbuds to listen to the music for the next minute.\n'\
        'Press enter to start.')

    mixer.quit()
    mixer.init()
    mixer.music.load('music/three songs.mp3')
    mixer.music.play(0,1)

    data, blinkCount = startEEG(65,[4,24,44,64]) #66s   [5,25,45,65]
    mixer.music.stop()
    print 'One moment, plotting your data....'
    #plotSong(data)
    data = array(data)

    numRuns = 0
    numRight = 0
    while 1:
        choice = raw_input('Hit 1 to have me guess a song or 2 to exit.')
        if choice == '1':
            numRuns += 1
            raw_input('Hit enter to listen to a random song.')
            songTitles = ["Paparazzi 20 seconds.mp3", "Mozart 20 seconds.mp3", "Sedated 20 seconds.mp3"]
            song = songTitles[int(floor(3*random(1)))]
            mixer.music.load('music/'+song)
            mixer.music.play(0,1)

            #Record the eeg for this song
            dataRandSong, blinkCount = startEEG(25,[4,24])
            mixer.music.stop()
            dataRandSong1 = array(dataRandSong)
            #normalize the data
            data2 = zeros([3,13])
            dataRandSong = dataRandSong1[1,0:13]/norm(dataRandSong1[1,0:13])
            data2[0,:] = data[1,0:13]/norm(data[1,0:13])
            data2[1,:] = data[2,0:13]/norm(data[2,0:13])
            data2[2,:] = data[3,0:13]/norm(data[3,0:13])
            
            #Find closest match between earlier data and this one
            result = dot(data2,dataRandSong)  #Comparing just alpha
            print result
            guess = where(result==max(result))[0][0]
            print 'I think you just heard song %i.' % (guess+1)
            choice = raw_input("Was I right? (y/n) ")
            if choice == "y":
                numRight+=1
                
        else:
            print "I got %i right out of %i guesses." % (numRight, numRuns)
            if raw_input('Save results? (y/n) ') == 'y':
            	filename = raw_input('Enter file name: ')
            	file = open(filename+".music", 'a')
            	pickle.dump([numRight, numRuns], file)
            	file.close()
            	print 'Saved to file...'
            break
    
    mixer.quit()
    raw_input('Hit enter to continue...')
    print('\n\n')
    
#################
# Demo 1: Raw EEG
################    
def expt3():
    print '-----------------------------'
    print 'Demo 1: Raw brain waves\n'
    raw_input('Hit enter to watch your EEG and Spectrum for 20s.')
    startEEG(20)
    raw_input('Hit enter to continue...')
    print('\n\n')


#################
# Demo 2: Brain music
################
def expt4():
    print '-------------------------'
    print 'Demo 2: Brain music'
    raw_input('This demo will record your brain signal for 15s and ' +
        'play it back at 2x time speed (so you can hear it). \n' \
        'Hit enter to start.')
    data, blinks=startEEG(15, music=True)    
    print 'One moment, playing your brain music...\n'
    mixer.quit()
    mixer.init(frequency=1024, size=-16, channels=1, buffer=4096)
    
    soundVals = []
    file = open("brain_music.raw",'r')
    for line in file:
        soundVals.append(int(line.rstrip('\n').split(',')[1]))
    file.close()
    soundVals = array(soundVals)
    sound = sndarray.make_sound(soundVals)
    mixer.Sound.play(sound)
    while mixer.get_busy():
    	time.sleep(1)
    mixer.quit()
    raw_input('Hit enter to continue...')
    print('\n\n')
    
#################
# Menu of experiments
################
options = ['Experiment 1: Blink detection', \
    'Experiment 2: Songs',\
    'Demo 1: Raw brain waves',\
    'Demo 2: Brain music',\
    'Exit']
        
callbacks = [expt1, expt2, expt3, expt4]

while True:
    close('all')
    print '  -----------------------------------'
    print '  -   Alex\'s Brain Waves Project    -'
    print '  -----------------------------------'
    print 'Choose a brain wave experiment to run:'  
    for i,option in enumerate(options):
        print('%s. %s' % (i+1, option)) # display all options
    choice = int(raw_input('Press the number of your choice? '))
    if choice == 5: break
    print '\n'
    callbacks[choice-1]() # call corresponding function 


print 'Bye!\n\n'


