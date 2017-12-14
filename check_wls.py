#!/usr/bin/python
import urllib2, json, base64, sys

#Weblogic user with monitoring rights
username = "nagios"
password = ""


(EXIT_OK, EXIT_WARNING, EXIT_CRITICAL, EXIT_UNKNOWN) = (0,1,2,3)

def main():
    try:
        #Check if correct parameters are entered
        if len(sys.argv) is 4:
            if sys.argv[1]=='--help':
                print("The syntax is: [server_address] [port] [check_type] [warning_threshold] [critical_threshold]")
                print("Check types: totalthread, threadhealth, stuckthreads and serverhealth")
                print("Do not specify thresholds for serverhealth and threadhealth")
                sys.exit(EXIT_UNKNOWN)
            elif sys.argv[3]=='serverhealth':
                output,exit = ServerHealth(SetBaseServer(sys.argv[1],sys.argv[2]))
            else:
                print("Syntax error. Try --help")
                sys.exit(EXIT_UNKNOWN)
        elif len(sys.argv) is 6:
            if sys.argv[3]=='totalthread':
                output,exit = TotalThread(SetBaseServer(sys.argv[1],sys.argv[2]),sys.argv[4],sys.argv[5])
            elif sys.argv[3]=='stuckthreads':
                output,exit = StuckThreads(SetBaseServer(sys.argv[1],sys.argv[2]),sys.argv[4],sys.argv[5])
            else:
                print("Syntax error. Try --help")
                sys.exit(EXIT_UNKNOWN)
        else:
            print("Wrong number of arguments passed to script. Try --help")
            sys.exit(EXIT_UNKNOWN)

        print output
        sys.exit(exit)

    except Exception as e:
        print("Error in main()")
        print str(e)
        sys.exit(UNKNOWN)

def SetBaseServer(srv_address, port):
    return "http://" + str(srv_address) + ":" + str(port)

def AuthenticateWithWLS(url):
    #HTTP authentication
    try:
        request = urllib2.Request(url)
        base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)
    except Exception as e:
        print ("Error in AuthenticateWithWLS(): "), str(e))
        sys.exit(EXIT_UNKNOWN)

    return request

def FetchAndParse(request):
    try:
            response = urllib2.urlopen(request)
            data = json.loads(response.read())
            return data
    except Exception as e:
            print ("Error in FetchAndParse(): ", str(e))
            sys.exit(EXIT_UNKNOWN)

def StuckThreads(baseserver,warn, crit):
    try:
        warning_threshold = int(warn)
        critical_threshold = int(crit)
    except Exception as e:
        print ("Error in StuckThreads() while setting crit and warn variables: ", str(e))
        sys.exit(EXIT_UNKNOWN)

    try:
        if warning_threshold >= critical_threshold:
            print ("Critical threshold must be higher than warning threshold")
            sys.exit(EXIT_UNKNOWN)

        targeturl1 = baseserver + "/management/wls/latest/servers"

        request1 = AuthenticateWithWLS(targeturl1)
        data1 = FetchAndParse(request1)
        exit = EXIT_OK
        result = ""

        for server in data1['items']:
            targeturl2 = baseserver + "/management/weblogic/latest/domainRuntime/serverRuntimes/"+server['name']+"/threadPoolRuntime"
            request2 = AuthenticateWithWLS(targeturl2)
            data2 = FetchAndParse(request2)

            if int(data2['stuckThreadCount']) >= warning_threshold and int(data2['stuckThreadCount']) < critical_threshold:
                result = "WARNING: " + str(data2['stuckThreadCount']) +" stuck threads on " + server['name'] +" - " + result
                if exit != EXIT_CRITICAL:
                    exit = EXIT_WARNING

            elif int(data2['stuckThreadCount']) >= critical_threshold:
                result = "CRITICAL: " + str(data2['stuckThreadCount']) +" stuck threads on " + server['name'] +" - " + result
                exit = EXIT_CRITICAL

        if exit == EXIT_OK:
            result = "OK! Number of stuck threads under warning limit"
        return (result,exit)

    except Exception as e:
        print ("Error in StuckThreads(): ",str(e))
        sys.exit(EXIT_UNKNOWN)

def ServerHealth(baseserver):
    try:
        targeturl = baseserver + "/management/wls/latest/servers"
        request = AuthenticateWithWLS(targeturl)
        data = FetchAndParse(request)
        exit = EXIT_OK
        result = ""

        for server in data['items']:
            if str(server['health']['state']) != "ok":
                result = result + server['name'] + " - state: " +server['health']['state'] + " - "
                exit = EXIT_CRITICAL
        if exit == EXIT_OK:
            result = "Server health is OK!"

        return(result,exit)

    except Exception as e:
        print ("Error in ServerHealth()",str(e))
        sys.exit(EXIT_UNKNOWN)

def TotalThread(baseserver, warn, crit):

    try:
        critical_threshold = int(crit)
        warning_threshold = int(warn)
    except Exception as e:
        print ("Error in TotalThread() while setting crit and warn variables: ", str(e))
        sys.exit(EXIT_UNKNOWN)

    try:
        if warning_threshold >= critical_threshold:
            print ("Critical threshold must be higher than warning threshold")
            sys.exit(EXIT_UNKNOWN)

        targeturl = baseserver + "/management/wls/latest"
        request = AuthenticateWithWLS(targeturl)
        data = FetchAndParse(request)

        totalThreadCount = data['item']['activeThreadCount']
        serverName = data['item']['name']
        result = "Total thread count: " + str(totalThreadCount) + " on " + serverName

        exit = EXIT_OK
        if totalThreadCount >= critical_threshold:
                result = "CRITICAL: "  + result
                exit = EXIT_CRITICAL
        elif totalThreadCount >= warning_threshold and totalThreadCount < critical_threshold:
                result = "WARNING: "  + result
                exit = EXIT_WARNING
        else:
                result = "OK! " + result

        return (result, exit)

    except Exception as e:
        print ("Error in TotalThread()", str(e))
        sys.exit(EXIT_UNKNOWN)


if __name__ == "__main__":
    main()
