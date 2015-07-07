'''
Created on Mar 15, 2011

@author: mkelse01
'''
from A_7001_01_BaseFlow import A_7001_01
from EdgeDbManager import EdgeDbManager
from HL7ReceiverManager import HL7ReceiverManager
from NistRepositoryManager import NistRepositoryManager
from time import localtime
from time import strftime
import sys
import os

tempRoot = '.';
mesaDir = '.';
mesaToolDir = '.';
dataRoot = '.';
dcm4CheDir = '.';


class A_7001_17():
    def run(self):
    
        print '''
        A_7001_17:
        '''
        
        global tempRoot;
        global mesaDir;
        global mesaToolDir;
        global dataRoot;
        global dcm4CheDir;
        
        self.verifyEnvironment();
        
        testName = 'A_7001_17';
        numberOfSeriesPerStudy = 1;
        numberOfSOPsPerSeries = 1;  # This is the number of dicom images sent per unique series
        
        ## Testing Hosts ##
        edgeHost = '172.20.175.63'
        
        
        ## PACS Host ##
        pacsAeTitle = 'DCM4CHEE';
        pacsHost = 'localhost';
        pacsPort = '11112';
        
        ## MIRTH HL7 Connection
        mirthHl7Host = edgeHost;
        mirthHl7Port = '20000';
        
        ## XDS Clearinghouse Connections
        nistScriptDirectory = '/usr/local/tomcat1/bin'
        registryURL = 'http://localhost:9080/axis2/services/xdsregistryb';
        repositoryURL = 'http://localhost:9080/axis2/services/xdsrepositoryb';
        repositoryUID = '1.19.6.24.109.42.1.5';
        PATIENT_ID_ASSIGNING_AUTHORITY = '1.3.6.1.4.1.19376.2.840.1.1.1.1';
        PATIENT_ID_ASSIGNING_AUTHORITY_TYPE = 'ISO';
        
        testDataDir = dataRoot + '/A-7001/A-7001-01';
        baseTest = A_7001_01(testName, tempRoot, dcm4CheDir, mesaDir, mesaToolDir, edgeHost);
    
        ## XDS HL7 Connection
        xdsHl7JarPath = os.path.normpath(os.getcwd() + '/../util/HL7Receiver.jar');
        xdsHl7Port = 9082;
        
        ## --------------------------------------------------------- ##
        print 'Starting XDS HL7 Receiver'
        ## --------------------------------------------------------- ##
        self.xdsHl7 = HL7ReceiverManager(xdsHl7JarPath, xdsHl7Port, False, False);
        if self.xdsHl7.isAnInstanceRunning():
            return (False, 'HL7 Receiver already running.  Kill process before testing.');
        success = self.xdsHl7.startServer();
        if not success:
            return (False, 'Failed to start HL7 Receiver');
    
        ## --------------------------------------------------------- ##
        print 'Starting NIST Repository as Clearinghouse'
        ## --------------------------------------------------------- ##
        self.nist = NistRepositoryManager(nistScriptDirectory);
        success = self.nist.startServer();
        if not success:
            return (False, 'Failed to start NIST Repository');

        ## --------------------------------------------------------- ##
        print 'Generate unique Study Instance UID'
        ## --------------------------------------------------------- ##
        studyUID = '9999.' + strftime('%Y%m%d%H%M%S', localtime());
        
        ## --------------------------------------------------------- ##
        print 'Generate dictionary used to fill hl7 message templates'
        ## --------------------------------------------------------- ##
        customFieldsDictionary = baseTest.generateCustomFields(studyUID);
        patientName = customFieldsDictionary['PATIENT_NAME'];
        print 'patientName:' + patientName;
        patientID = customFieldsDictionary['PATIENT_ID'];
        print 'patientID:' + patientID;
        accessionNumber = customFieldsDictionary['ACCESSION_NUMBER'];
        print 'accessionNumber:' + accessionNumber;
        studyUID = customFieldsDictionary['STUDY_INSTANCE_UID'];
        print 'studyUID:' + studyUID;
    
        # Create test directorys
        testTempDir = tempRoot + '/' + accessionNumber;
        os.makedirs(testTempDir);
        retreivedFilesDirectory = testTempDir + '/retrieved'; 
        os.makedirs(retreivedFilesDirectory);
        sentFilesDirectory = testTempDir + '/sent'; 
        os.makedirs(sentFilesDirectory);
    
        ## --------------------------------------------------------- ##
        print 'Generate ORM HL7 message and send to HL7 receiver - Creates Exam & Patient entries via MIRTH' 
        ## --------------------------------------------------------- ##
        status = baseTest.generateAndSendOrm(testDataDir, customFieldsDictionary, mirthHl7Host, mirthHl7Port);
        if(status != 'SCHEDULED'):
            return (False, 'Failed to schedule exam');
        
        ## --------------------------------------------------------- ##
        print 'Skip ORU HL7 creation and transmission' 
        ## --------------------------------------------------------- ##
        
        ## --------------------------------------------------------- ##
        print 'Prepare DICOM files to with Study, Series, SOP UIDs' 
        ## --------------------------------------------------------- ##
        studySeriesSopUIDs = [];
        # SeriesUID format - StudyUID.N
        # SopUID format    - StudyUID.Series.N
        #   where N is a reasonably unique int
        n = int(strftime('%H%M%S', localtime()));
        for seriesIndex in range(numberOfSeriesPerStudy):
            seriesN = seriesIndex + n;
            seriesUID = str(studyUID) + '.' + str(seriesN)
            for sopIndex in range(numberOfSOPsPerSeries):
                sopN = sopIndex + n;
                sopUID = str(seriesUID) + '.'+ str(sopN)
                studySeriesSopUIDs.append([studyUID, seriesUID, sopUID]);
        success = baseTest.generateCustomDicomFiles(studySeriesSopUIDs, customFieldsDictionary, testDataDir + '/dicom_files/MR.dcm', sentFilesDirectory)
        if not success:
            return (False, 'Failed to generate custom dicom files');
        
        ## --------------------------------------------------------- ##
        print 'Send DICOM files to PACS' 
        ## --------------------------------------------------------- ##
        baseTest.sendDicomFileToPacs(pacsAeTitle, pacsHost, pacsPort, sentFilesDirectory, customFieldsDictionary);
        
        
        ## --------------------------------------------------------- ##
        print 'Instruct EDGE to retrieve DICOM files for pid & accession - Job, JobSet, Transactions entries in rsnadb';  
        ## --------------------------------------------------------- ##
        jobID = baseTest.startNewJobAndTransactionOnEdge(patientID, accessionNumber);
        

        
        print 'Wait for EDGE to get to "Wait for report finalization" status' 
        ## --------------------------------------------------------- ##
        statusCode = baseTest.waitForTransactionStatusCode(jobID, 21, 240);
        if(statusCode != 21):
            return (False, 'Transaction status code set to: ' +  str(statusCode) + ' Expected 21.');
            
        ## --------------------------------------------------------- ##
        print 'Update transaction status to GO (30)' 
        ## --------------------------------------------------------- ##
        baseTest.updateTransactionStatusCode(jobID, 30);   
            
        ## --------------------------------------------------------- ##
        ## --------------------------------------------------------- ##
        print 'Wait for EDGE to get to "Failed to generate KOS" status' 
        ## --------------------------------------------------------- ##
        statusCode = baseTest.waitForTransactionStatusCode(jobID, -32, 240);
        if(statusCode != -32):
            return (False, 'Transaction status code set to: ' +  str(statusCode) + ' Expected 21.');

        
        ## --------------------------------------------------------- ##
        print 'Retrieve XDS documents from Clearinghouse repository'  
        ## --------------------------------------------------------- ##
        PATIENT_ID_ASSIGNING_AUTHORITY = '1.3.6.1.4.1.19376.2.840.1.1.1.1';
        PATIENT_ID_ASSIGNING_AUTHORITY_TYPE = 'ISO';
        singleUsePatientID = EdgeDbManager('rsnadb', edgeHost, 'edge', 'd17bK4#M').getSingleUsePatientID(jobID);
        fullPatientID = singleUsePatientID + r'^^^&' + PATIENT_ID_ASSIGNING_AUTHORITY + r'&' + PATIENT_ID_ASSIGNING_AUTHORITY_TYPE;
        baseTest.retrieveXdsDocuments(fullPatientID, registryURL, repositoryURL, repositoryUID, retreivedFilesDirectory);
          
        ## --------------------------------------------------------- ##
        print 'Expect transaction status code -32 and zero matching documents.'  
        ## --------------------------------------------------------- ##
        if(statusCode != -32):
            return (False, 'Transaction status code set to: ' +  str(statusCode));
        elif len(os.listdir(retreivedFilesDirectory)) > 0 :
            return (False, 'Unexpected documents retrieved');
        else:
            print 'Transaction status:', statusCode, 'Zero matching documents retrieved.'
            
        success = self.nist.startServer();
        return (True, 'Passed Tests'); 
    
    def cleanup(self):
        self.nist.stopServer();
        
    def verifyEnvironment(self):
        global tempRoot;
        global mesaDir;
        global mesaToolDir;
        global dataRoot;
        global dcm4CheDir;
        ## Verify environment
        if not 'MESA_TARGET' in os.environ:
            print "Missing MESA_TARGET"
            exit(1)
        else:
            mesaDir = os.environ['MESA_TARGET'];
            mesaToolDir = mesaDir + '/bin';
    
        if not 'VERIF_VALID_HOME' in os.environ:
            print "Missing VERIF_VALID_HOME"
            exit(1)
        else:
            dataRoot = os.environ['VERIF_VALID_HOME'] + '/data';
    
        if not 'DCM4CHE_HOME' in os.environ:
            print "Missing DCM4CHE_HOME"
            exit(1)
        else:
            dcm4CheDir = os.environ['DCM4CHE_HOME'];
            
        if not 'TEMP' in os.environ:
            tempRoot = '/tmp';
        else:
            tempRoot = os.environ['TEMP'];
    

if __name__ == "__main__":
    print 'Running A_7001_17 as main()'
    test = A_7001_17();
    testPassed, message = test.run();
    print message;
    test.cleanup();
    sys.exit(0) # exit indicating normal execution