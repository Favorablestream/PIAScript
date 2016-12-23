#!/usr/bin/env python3

#License
'''
    MIT License

    Copyright (c) 2016 Kieran Gillibrand

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the 'Software'), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
'''
    
#Description
'''
    PIA Port Forwarding Script
    
    A small script which enables port forwarding for a Private Internet Access VPN and displays the forwarded port.
'''

#Metadata
__title__ = 'Private Internet Access Port Forwarding Script'
__author__ = 'Kieran Gillibrand'
__host__ = 'https://github.com/Favorablestream'
__copyright__ = 'Copyright 2016 Kieran Gillibrand'
__credits__ = ['Duncan Gillibrand']
__license__ = 'MIT License (LICENSE.txt)'
__version__ = '1.2'
__date__ = '23/12/2016'
__maintainer__ = 'Kieran Gillibrand'
__email__ = 'Kieran.Gillibrand6@gmail.com'
__status__ = 'Personal Project (released)'

#Imports
import netifaces

import argparse

import urllib.request
import urllib.parse
import urllib.error

import json

import sys

#Global Constants
DEBUG = False
'''Flag for debugging print statements (set by -debug/--debug command line option)'''

DEFAULT_ENCODING = 'utf-8'
'''Default encoding to use for decoding the API response if the server does not give us an encoding header'''
    
#Code
def debugPrint (message: str, printNewline: bool = True):
    '''
        Print a message if debugging statements are enabled
        
        message (str): The message to print
        printNewline (bool): Print an additional newline after the message (default True) 
    '''
    
    if message == None:
        return
        
    if not DEBUG:
        return
        
    print (message)
    
    if printNewline:
        print ()
        
def nonDebugPrint (message: str, printNewline: bool = True):
    '''
        Print a message if debugging statements are not enabled
        
        message (str): The message to print
        printNewline (bool): Print an additional newline after the message (default True)
    '''
    
    if message == None:
        return
        
    if DEBUG:
        return
        
    print (message)
    
    if printNewline:
        print ()

def concatStringToList (message: str, elements: list) -> str:
    '''
        Concatenate a message string to a list of elements (str)
        
        Usually used to form an error message to pass to handleError when a list of addresses, elemts, etc is involved.
        
        message (str): The message before the elements are concatonated to it
        elements (list): The list of elements to concatenate to the message
    '''
        
    stringElements = []
    
    for element in elements:
        stringElements.append (str (element))
        
    return message + ('\n'.join (stringElements)) #Join all elements delimited by a newline to the message and return
    
def handleError (message: str, exitCode: int, exception: Exception = None):
    '''
        Prints an error message, exception message (if provided), and exits with the given exit code
        
        message (str): The error message to print
        exception (Exception) (optional): The exception used to print the provided esception message
        exitCode (int): The code to exit with
        
        Script Exit Codes
        - 0: main (): Success, normal exit
        - 1: main (): VPN is not connected
        - 2: getCredentials (): Credentials file cannot be opened
        - 3: getCredentials (): JSON credentials are malformed
        - 4: getCredentials (): JSON credentials file is missing some required keys
        - 5: getIPAddress (): Found more addresses than expected
        - 6: forwardPort (): Error posting to API endpoint
        - 7: forwardPort (): API JSON response is malformed
        - 8: main (): API returned an error response
        - 9: main (): API returned an unknown response
    '''
    
    exitCodes = ['main (): Success, normal exit', 'main (): VPN is not connected', 'getCredentials (): Credentials file cannot be opened', 'getCredentials (): JSON credentials are malformed', 'getCredentials (): Credentials file is missing required keys', 'getIPAddress (): Found more addresses than expected', 'forwardPort (): Error posting to API endpoint', 'forwardPort (): API JSON response is malformed', 'main (): API returned an error response', 'main (): API returned an unknown response']
    
    print (message)
    print ()
    
    if exception != None:
        print (str (exception))
        print ()
        
    print ('Exiting with exit status: %s, %s' %(exitCode, exitCodes [exitCode]))
    
    sys.exit (exitCode)
    
def isConnected (interface: str) -> bool:
    '''
        Checks if the VPN is connected (Boolean)
        
        interface (str): The name of the interface to check
    '''

    exists = interface in netifaces.interfaces () #Check if the interface exists
    
    #We cannot be connected if the interface does not exist
    if not exists:
        return False
        
    #Check if IPV4 is contained in the address families for the interface (if it has at least one IPV4 address and therefore is up)
    addressFamilies = netifaces.ifaddresses (interface)
    up = netifaces.AF_INET in addressFamilies
    
    if up:
        debugPrint ('Interface: \'%s\' is connected' %interface)

    return up

def getIPAddress (interface: str) -> str:
    '''
        Returns the IPV4 address of the interface (str)
        
        interface (str): The name of the interface to get the IP for
    '''

    ADDRESS_LIMIT = 1
    '''Number of IPV4 addresses expected for the interface. Having more than 1 IP for the VPN is not expected'''
    
    #Confusing networking stuff that I sort of understand. See: https://pypi.python.org/pypi/netifaces or https://alastairs-place.net/projects/netifaces/
    addressFamilies = netifaces.ifaddresses (interface) #All address families for the interface
    addressList = addressFamilies [netifaces.AF_INET] #List of addresses for the IPV4 family
    
    addresses = len (addressList)

    #Exit if we get more than one IPV4 address for the family
    if addresses > ADDRESS_LIMIT:
        message = concatStringToList ('Receieved %d IPV4 address(es) for your VPN interface: \'%s\', expected: %s\nAddresses:\n\n' %(addresses, interface, ADDRESS_LIMIT), addressList)
                
        handleError (message = message, exitCode = 5)
        
    address = addressList [0] #First address in the list (at this point we should only have one)
    ip = address ['addr'] #The address itself (peer and netmask are also returned)

    debugPrint ('Local IP for VPN interface \'%s\': %s' %(interface, ip))

    return ip

def getCredentials (credentialsPath: str, interface: str) -> dict:
    '''
        Retrieves PIA API credentials from a file and loads them into a JSON Dictionary (Dictionary)
            
        credentialsPath (str): The path to the credentials JSON file
        interface (str): The VPN interface to get the local IP from
    '''
        
    try:
        with open (credentialsPath) as credentialsFile:
            debugPrint ('Using credentials file: \'%s\'' %credentialsPath)
                    
            credentials = json.loads (credentialsFile.read ())

    except (IOError, OSError) as fileError:
        handleError (message = 'Credentials file: \'%s\' does not exist or cannot be opened' %credentialsPath, exception = fileError, exitCode = 2)
        
    except (ValueError) as jsonError:
        handleError (message = 'JSON file: \'%s\' is malformed, refer to the README or the exception message below for the correct format' %credentialsPath, exception = jsonError, exitCode = 3)
            
    credentials ['local_ip'] = getIPAddress (interface) #Add local VPN IP
    
    #Exit if username, password, or client ID is missing
    if not credentials.keys () & {'user', 'pass', 'client_id'}:
        handleError (message = 'Credentials file: %s is missing required keys. See the required format in the README' %credentialsPath, exitCode = 4)

    debugPrint ('Username: \'%s\'' %credentials ['user'], printNewline = False)
    debugPrint ('Password: \'%s\'' %credentials ['pass'], printNewline = False)
    debugPrint ('Client ID: \'%s\'' %credentials ['client_id'])
    
    return credentials
                        
def forwardPort (credentials: dict, endpointURL: str, timeout: int) -> dict:
    '''
        Contacts the PIA API to enable port forwarding and returns the parsed API response (Dictionary)

        credentials (Dictionary): The credentials extracted from a JSON file by getPIACredentials ()
        url (str): The endpoint URL to post to
        encoding (str): The text encoding to decode the API response bytes into
        timeout (int): The number of seconds before the API connection times out
    '''

    debugPrint ('Posting to endpoint: \'%s\'' % endpointURL)

    parameters = urllib.parse.urlencode (credentials)
    
    parametersBytes = str.encode (parameters)
    
    try:
        with urllib.request.urlopen (url = endpointURL, data = parametersBytes, timeout = timeout) as connection:
            response = connection.read ()
            
            #Decode with the given encoding or with the default if none is given
            responseEncoding = connection.headers.get_content_charset ()
            if responseEncoding == None:
                responseEncoding = DEFAULT_ENCODING
        
    except (urllib.error.URLError, urllib.error.HTTPError) as urlError:
        handleError (message = 'Error posting to endpoint URL: %s' %endpointURL, exception = urlError, exitCode = 6)
        
    responseString = response.decode (responseEncoding)

    nonHTTPResponse = urllib.parse.unquote (responseString) #Remove URL encoding, doesn't matter for the responses from this API in my experience

    debugPrint ('Decoded API response bytes as: \'%s\'' %responseEncoding)
    debugPrint ('API response JSON: \'%s\'' %nonHTTPResponse)

    try:
        return json.loads (nonHTTPResponse)
    
    except (ValueError) as jsonError:
        handleError (message = 'The API response is malformed, refer to the response text and the exception message below\n\nResponse text: %s' %nonHTTPResponse, exception = jsonError, exitCode = 7)

def main ():
    '''Main method that takes command line arguments'''
    
    #Local Constants
    ENDPOINT = 'https://www.privateinternetaccess.com/vpninfo/port_forward_assignment'
    '''API endpoint URL'''

    INTERFACE = 'tun0'
    '''Network interface for VPN'''
    
    TIMEOUT = 10
    '''Timeout in seconds when connecting to the API endpoint'''

    print ()
    print ('%s - %s, %s' %(__title__, __copyright__, __license__))
    print ('Version: %s, %s' %(__version__, __date__))
    print ('%s' %__host__)
    print ()
    
    parser = argparse.ArgumentParser (description = 'PIA Port Forwarding Script: A small script which enables port forwarding for a Private Internet Access VPN and displays the forwarded port.')
    parser.add_argument ('-debug', '--debug', help = 'Display debugging print statements', action = 'store_true')
    parser.add_argument ('credentialsfile', help = 'The PIA API JSON credentials file, see README.md for details')
    args = parser.parse_args ()

    #Set global debug flag if -debug/--debug command line flag is used
    global DEBUG
    DEBUG = args.debug

    debugPrint ('Debugging print statements enabled')

    if not isConnected (INTERFACE):
        handleError (message = 'VPN interface: \'%s\' is not connected, please connect it first\nBe sure the INTERFACE variable is correctly set if your VPN is actually connected' %INTERFACE, exitCode = 1)

    credentials = getCredentials (credentialsPath = args.credentialsfile, interface = INTERFACE)
    
    response = forwardPort (credentials = credentials, endpointURL = ENDPOINT, timeout = TIMEOUT)

    nonDebugPrint ('Response recieved')

    #Standard response
    if 'port' in response:
        print ('Forwarded port: %s' %response ['port'])
        print ()

    #Error response
    elif 'error' in response:
        handleError (message = 'API returned an error: %s' %response ['error'], exitCode = 8)
        
    #Unknown key
    else:
        keyValues = []
        
        for key, value in response.items ():
            keyValues.append ('%s: %s' %(str (key), str (value)))
            
        message = concatStringToList ('API returned unknown key/value pair(s):\n\n', keyValues)

        handleError (message = message, exitCode = 9)

    print ('Make sure to allow this port in your firewall and configure your applications to use it.')
    print ('Have a nice day :)')
    
if  __name__ == '__main__':
    main ()