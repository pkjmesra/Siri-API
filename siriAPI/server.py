import http.server
import socketserver
import threading
import time
import os

from .document import document

os.chdir(os.path.dirname(os.path.realpath(__file__))) #Make sure to change the working directory to import html, css and pac file

class _Handler(http.server.SimpleHTTPRequestHandler):
    def __init__ (self, siri_api, *args):
        self.siri_api = siri_api
        http.server.SimpleHTTPRequestHandler.__init__(self, *args)
        
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

    def do_GET(self):
        parts = self.path.split("?") #Extract requested file and get parameters from path
        path = parts[0]
        
        #Extract variables from get parameters
        try:
            arguments = {}
            arguments["q"] = None #Variable for search request. Default None to prevent errors if no search request was started
            if (len(parts) > 1):
                raw_arguments = parts[1].split("&")
                for raw_argument in raw_arguments[:]:
                    argument = raw_argument.split("=", 1)
                    arguments[argument[0]] = argument[1]
        except:
            print ("No get parameters")
        
        
        #Decide whether a search or the style.css was requested
        if (path == "/style.css"):
            self.document = open('style.css', 'r').read()
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes(self.document, "utf-8"))
        elif (path == "/proxy.pac"):
            self.document = open('proxy.pac', 'r').read()
            self.document = self.document.replace('<keyword>', self.siri_api.keyword.lower(), 1)
            self.document = self.document.replace('<google_domain>', self.siri_api.google_domain, 1)
            
            if (self.siri_api.yahoo_domain == None):
                self.document = self.document.replace('<yahoo_domain>', "nodomain", 1)
            else:
                self.document = self.document.replace('<yahoo_domain>', self.siri_api.yahoo_domain, 1)
            self.document = self.document.replace('<squid_host>', self.siri_api.squid.get_hostname(), 2)
            self.document = self.document.replace('<squid_port>', str(self.siri_api.squid.port), 2)
            self.send_response(200)
            self.send_header('Cache-Control', 'public,max-age=%d' % int(3600*48))
            self.send_header('Content-type', 'application/x-ns-proxy-autoconfig')
            self.end_headers()
            self.wfile.write(bytes(self.document, "utf-8"))
        elif (path == "/done"):
            self.output = document(self)
            self.output.use_chat_style (True)
            self.output.title ('Reload lock')
            self.output.error ('The action has already been performed. To protect it from another execution after a browser restart, you have to open it using Siri. <a href="https://github.com/HcDevel/Siri-API/wiki/FAQ-%28Version-1.1.x%29#what-is-the-reload-lock">Read more...</a>')
            self.output.send()
        elif (arguments["q"] != None):
            arguments["q"] = arguments["q"].replace(self.siri_api.keyword + '+', '', 1)
            arguments["q"] = arguments["q"].replace('+', ' ')
            self.output = document(self)
            self.siri_api.search.search(arguments["q"], self.output)
            if (self.output.sent == False):
                self.output.use_chat_style (True)
                self.output.title ('Exception')
                self.output.incoming (arguments["q"])
                self.output.outgoing ('You have to call output.send() after the output is ready to transfer')
                self.output.send()
                raise Exception ('You have to call output.send() after the output is ready to transfer')
        elif (arguments["p"] != None):
            arguments["p"] = arguments["p"].replace('+', ' ')
            self.output = document(self)
            self.siri_api.search.search(arguments["p"], self.output)
            if (self.output.sent == False):
                self.output.use_chat_style (True)
                self.output.title ('Exception')
                self.output.incoming (arguments["p"])
                self.output.outgoing ('You have to call output.send() after the output is ready to transfer')
                self.output.send()
                raise Exception ('You have to call output.send() after the output is ready to transfer')
        else:
            self.send_response(404)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes('Not found. Please visit <a href="https://github.com/HcDevel/Siri-API/wiki/_pages">https://github.com/HcDevel/Siri-API/wiki/_pages</a>', "utf-8"))

        return
        
    #def log_message(self, format, *args): #Disable logging
    #    pass
        
    #def log_error(self, format, *args):
    #    pass
    
class server:
    def __init__(self, siri_api):
        self.siri_api = siri_api #Parent SiriAPI class instance
        self.port = 3030
        self.hostname = None
        self.httpd = None
      
    #Hostname
    def set_hostname (self, hostname):
        if (isinstance(hostname, str)):
            self.hostname = hostname
            self.siri_api.hostname = hostname
        else:
            raise Exception("Hostname has to be a string")
            
    def get_hostname (self):
        return (self.hostname)
    
    #Port
    def set_port (self, port):
        if (isinstance(port, int)):
            self.port = port
        else:
            raise Exception("Port has to be an integer")
            
    def get_port (self):
        return (self.port)
        
    #Start server
    def start (self, force=False):
        if (self.hostname == None):
            raise Exception ("Hostname for the server has to be set")
        elif (self.siri_api.google_domain == None):
            raise Exception ("Google domain has to be set")
        else:
            if (self.httpd == None):
                exception = True
                tried = 0
                while (exception == True and (tried == 0 or force == True)): #Solves trouble in autostart mode (when network isn't ready)
                    tried += 1
                    try:
                        self.httpd = socketserver.TCPServer(('', self.port), lambda *args: _Handler(self.siri_api, *args))
                        threading.Thread(target=self.httpd.serve_forever).start()
                        print('Success: Server listening on port ' + str(self.port) + '...')
                        exception = False
                    except:
                        raise Exception ("Error: Webserver can't be started")
                        time.sleep (1)
            else:
                print ("Server is already running")
        
    #Stop server
    def stop (self):
        if (self.httpd != None):
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
            print ("Success: Server stopped")
        else:
            print ("Error: No running instance of the webserver found")

class server_old:
    def __init__ (self, keywords=None, squid_hostname=None, google_domain=None, keyword="Siri", port=3030, squid_port=3128):
        self.httpd = None
        if (keywords == None or squid_hostname == None or google_domain == None):
            print ('Error: server() has the following syntax: (keywords, squid_hostname, google_domain, keyword="Siri", port=3030, squid_port=3128)')
            return
        else:
            self.keywords = keywords
            self.squid_hostname = squid_hostname
            self.google_domain = google_domain
            self.keyword = keyword
            self.port = port
            self.squid_port = squid_port
            
    def start (self, force=False):
        if (self.httpd == None):
            exception = True
            tried = 0
            while (exception == True and (tried == 0 or force == True)): #Solves trouble in autostart mode (when network isn't ready)
                tried += 1
                try:
                    #self.httpd = socketserver.TCPServer(('', self.port), _Handler)
                    self.httpd = socketserver.TCPServer(('', self.port), lambda *args: _Handler(self.squid_hostname, self.squid_port, self.google_domain, self.keyword, *args))
                    threading.Thread(target=self.httpd.serve_forever).start()
                    print('Success: Server listening on port ' + str(self.port) + '...')
                    exception = False
                except:
                    print ("Error: Webserver can't be started")
                    time.sleep (1)
        else:
            print ("Server is already running")
        
    def stop (self):
        if (self.httpd != None):
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
            print ("Success: Server stopped")
        else:
            print ("Error: No running instance of the webserver found")