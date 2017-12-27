#!/usr/bin/python
import urllib2, json, base64, sys

(EXIT_OK, EXIT_WARNING, EXIT_CRITICAL, EXIT_UNKNOWN) = (0,1,2,3)

def main():
    try:
        #Check if correct parameters are entered
        if len(sys.argv) is 2:
            if sys.argv[1] == "--help":
                print("The syntax is: [server_address] [port] [username] [password] [check_type] [warning_threshold] [critical_threshold]")
                print("Check types: totalthreads, stuckthreads and serverhealth")
                print("Do not specify any thresholds for serverhealth")
                sys.exit(EXIT_UNKNOWN)
            else:
                print("Syntax error. Try --help")
                sys.exit(EXIT_UNKNOWN)
        elif len(sys.argv) is 6:
            if sys.argv[5]=='serverhealth':
                output,exit = ServerHealth(SetBaseServer(sys.argv[1],sys.argv[2]),sys.argv[3],sys.argv[4])
            else:
                print("Syntax error. Try --help")
                sys.exit(EXIT_UNKNOWN)
        elif len(sys.argv) is 8:
            if sys.argv[5]=='totalthreads':
                output,exit = TotalThreads(SetBaseServer(sys.argv[1],sys.argv[2]),sys.argv[6],sys.argv[7],sys.argv[3],sys.argv[4])
            elif sys.argv[5]=='stuckthreads':
                output,exit = StuckThreads(SetBaseServer(sys.argv[1],sys.argv[2]),sys.argv[6],sys.argv[7],sys.argv[3],sys.argv[4])
            else:
                print("Syntax error. Try --help")
                sys.exit(EXIT_UNKNOWN)
        else:
            print("Syntax error. Try --help")
            sys.exit(EXIT_UNKNOWN)

        print output
        sys.exit(exit)

    except Exception as e:
        print("Error in main()")
        print str(e)
        sys.exit(UNKNOWN)

def SetBaseServer(srv_address, port):
    return "http://" + str(srv_address) + ":" + str(port)

def AuthenticateWithWLS(url, username, password):
    #HTTP authentication
    try:
        request = urllib2.Request(url)
        base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)
    except Exception as e:
        print ("Error in AuthenticateWithWLS(): ", str(e))
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

def StuckThreads(baseserver,warn,crit,username,password):
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

        request1 = AuthenticateWithWLS(targeturl1,username,password)
        data1 = FetchAndParse(request1)
        exit = EXIT_OK
        result = ""

        for server in data1['items']:
            if server['state'] != "running":
                print ("CRITICAL! Some servers are not running!")
                sys.exit(EXIT_CRITICAL)

            targeturl2 = baseserver + "/management/weblogic/latest/domainRuntime/serverRuntimes/"+server['name']+"/threadPoolRuntime"
            request2 = AuthenticateWithWLS(targeturl2,username,password)
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

def ServerHealth(baseserver,username,password):
    try:
        targeturl = baseserver + "/management/wls/latest/servers"
        request = AuthenticateWithWLS(targeturl,username,password)
        data = FetchAndParse(request)
        exit = EXIT_OK
        result = ""

        for server in data['items']:
            if 'health' in server:
                if str(server['health']['state']) != "ok":
                    result = result + server['name'] + " - state: " +server['health']['state'] + " - "
                    exit = EXIT_CRITICAL
            else:
                result = "CRITICAL! Unable to retrieve server health status from one or more servers!"
                exit = EXIT_CRITICAL
        if exit == EXIT_OK:
            result = "Server health is OK!"

        return(result,exit)

    except Exception as e:
        print ("Error in ServerHealth()",str(e))
        sys.exit(EXIT_UNKNOWN)

def TotalThreads(baseserver, warn, crit,username,password):

    try:
        critical_threshold = int(crit)
        warning_threshold = int(warn)
    except Exception as e:
        print ("Error in totalthreads() while setting crit and warn variables: ", str(e))
        sys.exit(EXIT_UNKNOWN)

    try:
        if warning_threshold >= critical_threshold:
            print ("Critical threshold must be higher than warning threshold")
            sys.exit(EXIT_UNKNOWN)

        targeturl = baseserver + "/management/wls/latest"
        request = AuthenticateWithWLS(targeturl,username,password)
        data = FetchAndParse(request)

        totalthreadsCount = data['item']['activeThreadCount']
        serverName = data['item']['name']
        result = "Total thread count: " + str(totalthreadsCount) + " on " + serverName

        exit = EXIT_OK
        if totalthreadsCount >= critical_threshold:
                result = "CRITICAL: "  + result
                exit = EXIT_CRITICAL
        elif totalthreadsCount >= warning_threshold and totalthreadsCount < critical_threshold:
                result = "WARNING: "  + result
                exit = EXIT_WARNING
        else:
                result = "OK! " + result

        return (result, exit)

    except Exception as e:
        print ("Error in totalthreads()", str(e))
        sys.exit(EXIT_UNKNOWN)


if __name__ == "__main__":
    main()
