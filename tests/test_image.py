import pytest
import re
import requests
import signal
import testinfra
import time

from helpers import get_app_home, get_app_install_dir, get_bootstrap_proc, get_procs, \
    parse_properties, parse_xml, run_image, \
    wait_for_http_response, wait_for_proc, wait_for_state, wait_for_log


PORT = 8080
STATUS_URL = f'http://localhost:{PORT}/status'

def test_server_xml_defaults(docker_cli, image):
    container = run_image(docker_cli, image)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    xml = parse_xml(container, f'{get_app_install_dir(container)}/conf/server.xml')
    connector = xml.find('.//Connector')
    valve = xml.find('.//Valve[@className="org.apache.catalina.valves.AccessLogValve"]')

    assert connector.get('port') == '8080'
    assert connector.get('maxThreads') == '100'
    assert connector.get('minSpareThreads') == '10'
    assert connector.get('connectionTimeout') == '20000'
    assert connector.get('enableLookups') == 'false'
    assert connector.get('protocol') == 'HTTP/1.1'
    assert connector.get('acceptCount') == '10'
    assert connector.get('secure') == 'false'
    assert connector.get('scheme') == 'http'
    assert connector.get('proxyName') == ''
    assert connector.get('proxyPort') == ''
    assert connector.get('maxHttpHeaderSize') == '8192'

    assert valve.get('maxDays') == '-1'


def test_server_xml_params(docker_cli, image):
    environment = {
        'ATL_TOMCAT_MGMT_PORT': '8006',
        'ATL_TOMCAT_PORT': '9090',
        'ATL_TOMCAT_MAXTHREADS': '201',
        'ATL_TOMCAT_MINSPARETHREADS': '11',
        'ATL_TOMCAT_CONNECTIONTIMEOUT': '20001',
        'ATL_TOMCAT_ENABLELOOKUPS': 'true',
        'ATL_TOMCAT_PROTOCOL': 'org.apache.coyote.http11.Http11Protocol',
        'ATL_TOMCAT_ACCEPTCOUNT': '11',
        'ATL_TOMCAT_SECURE': 'true',
        'ATL_TOMCAT_SCHEME': 'https',
        'ATL_PROXY_NAME': 'jira.atlassian.com',
        'ATL_PROXY_PORT': '443',
        'ATL_TOMCAT_MAXHTTPHEADERSIZE': '8193',
        'ATL_TOMCAT_CONTEXTPATH': '/myjira',
        'ATL_TOMCAT_ACCESS_LOGS_MAXDAYS': '10',
    }
    container = run_image(docker_cli, image, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    xml = parse_xml(container, f'{get_app_install_dir(container)}/conf/server.xml')
    connector = xml.find('.//Connector')
    context = xml.find('.//Context')
    valve = xml.find('.//Valve[@className="org.apache.catalina.valves.AccessLogValve"]')

    assert xml.get('port') == environment.get('ATL_TOMCAT_MGMT_PORT')

    assert connector.get('port') == environment.get('ATL_TOMCAT_PORT')
    assert connector.get('maxThreads') == environment.get('ATL_TOMCAT_MAXTHREADS')
    assert connector.get('minSpareThreads') == environment.get('ATL_TOMCAT_MINSPARETHREADS')
    assert connector.get('connectionTimeout') == environment.get('ATL_TOMCAT_CONNECTIONTIMEOUT')
    assert connector.get('enableLookups') == environment.get('ATL_TOMCAT_ENABLELOOKUPS')
    assert connector.get('protocol') == environment.get('ATL_TOMCAT_PROTOCOL')
    assert connector.get('acceptCount') == environment.get('ATL_TOMCAT_ACCEPTCOUNT')
    assert connector.get('secure') == environment.get('ATL_TOMCAT_SECURE')
    assert connector.get('scheme') == environment.get('ATL_TOMCAT_SCHEME')
    assert connector.get('proxyName') == environment.get('ATL_PROXY_NAME')
    assert connector.get('proxyPort') == environment.get('ATL_PROXY_PORT')
    assert connector.get('maxHttpHeaderSize') == environment.get('ATL_TOMCAT_MAXHTTPHEADERSIZE')

    assert context.get('path') == environment.get('ATL_TOMCAT_CONTEXTPATH')

    assert valve.get('maxDays') == environment.get('ATL_TOMCAT_ACCESS_LOGS_MAXDAYS')


def test_dbconfig_xml_defaults_postgres(docker_cli, image):
    environment = {
        'ATL_DB_TYPE': 'postgres72',
        'ATL_DB_DRIVER': 'org.postgresql.Driver',
        'ATL_JDBC_URL': 'jdbc:postgresql://mypostgres.mycompany.org:5432/jiradb',
        'ATL_JDBC_USER': 'jiradbuser',
        'ATL_JDBC_PASSWORD': 'jiradbpassword',
    }
    container = run_image(docker_cli, image, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    xml = parse_xml(container, f'{get_app_home(container)}/dbconfig.xml')

    assert xml.findtext('.//connection-properties') == 'tcpKeepAlive=true;socketTimeout=240'

    assert xml.findtext('.//pool-min-size') == '20'
    assert xml.findtext('.//pool-max-size') == '100'
    assert xml.findtext('.//pool-min-idle') == '10'
    assert xml.findtext('.//pool-max-idle') == '20'

    assert xml.findtext('.//pool-max-wait') == '30000'
    assert xml.findtext('.//validation-query') == 'select 1'
    assert xml.findtext('.//validation-query-timeout') is None
    assert xml.findtext('.//time-between-eviction-runs-millis') == '30000'
    assert xml.findtext('.//min-evictable-idle-time-millis') == '5000'

    assert xml.findtext('.//pool-remove-abandoned') == 'true'
    assert xml.findtext('.//pool-remove-abandoned-timeout') == '300'
    assert xml.findtext('.//pool-test-while-idle') == 'true'
    assert xml.findtext('.//pool-test-on-borrow') == 'false'


def test_dbconfig_xml_defaults_mysql(docker_cli, image):
    environment = {
        'ATL_DB_TYPE': 'mysql8',
        'ATL_DB_DRIVER': 'com.mysql.jdbc.Driver',
        'ATL_JDBC_URL': 'jdbc:mysql://mypostgres.mycompany.org:5432/jiradb',
        'ATL_JDBC_USER': 'jiradbuser',
        'ATL_JDBC_PASSWORD': 'jiradbpassword',
    }
    container = run_image(docker_cli, image, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    xml = parse_xml(container, f'{get_app_home(container)}/dbconfig.xml')

    assert xml.findtext('.//connection-properties') is None

    assert xml.findtext('.//pool-min-size') == '20'
    assert xml.findtext('.//pool-max-size') == '100'
    assert xml.findtext('.//pool-min-idle') == '10'
    assert xml.findtext('.//pool-max-idle') == '20'

    assert xml.findtext('.//pool-max-wait') == '30000'
    assert xml.findtext('.//validation-query') == 'select 1'
    assert xml.findtext('.//validation-query-timeout') == '3'
    assert xml.findtext('.//time-between-eviction-runs-millis') == '30000'
    assert xml.findtext('.//min-evictable-idle-time-millis') == '5000'

    assert xml.findtext('.//pool-remove-abandoned') == 'true'
    assert xml.findtext('.//pool-remove-abandoned-timeout') == '300'
    assert xml.findtext('.//pool-test-while-idle') == 'true'
    assert xml.findtext('.//pool-test-on-borrow') == 'false'


@pytest.mark.parametrize('atl_db_type', ['mssql', 'mysql', 'mysql57', 'mysql8', 'oracle10g', 'postgres72', 'dummyvalue'])
def test_dbconfig_xml_default_schema_names(docker_cli, image, run_user, atl_db_type):
    default_schema_names = {
        'mssql': 'dbo',
        'mysql': '',
        'mysql57': '',
        'mysql8': '',
        'oracle10g': '',
        'postgres72': 'public',
    }
    schema_name = default_schema_names.get(atl_db_type, '')

    environment = {
        'ATL_DB_TYPE': atl_db_type,
    }
    container = run_image(docker_cli, image, user=run_user, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    xml = parse_xml(container, f'{get_app_home(container)}/dbconfig.xml')

    assert xml.findtext('.//schema-name') == schema_name


def test_dbconfig_xml_params_postgres(docker_cli, image, run_user):
    environment = {
        'ATL_DB_TYPE': 'postgres72',
        'ATL_DB_DRIVER': 'org.postgresql.Driver',
        'ATL_JDBC_URL': 'jdbc:postgresql://mypostgres.mycompany.org:5432/jiradb',
        'ATL_JDBC_USER': 'jiradbuser',
        'ATL_JDBC_PASSWORD': 'jiradbpassword',
        'ATL_DB_SCHEMA_NAME': 'private',
        'ATL_DB_KEEPALIVE': 'false',
        'ATL_DB_SOCKETTIMEOUT': '999',
        'ATL_DB_MAXIDLE': '21',
        'ATL_DB_MAXWAITMILLIS': '30001',
        'ATL_DB_MINEVICTABLEIDLETIMEMILLIS': '5001',
        'ATL_DB_MINIDLE': '11',
        'ATL_DB_POOLMAXSIZE': '101',
        'ATL_DB_POOLMINSIZE': '21',
        'ATL_DB_REMOVEABANDONED': 'false',
        'ATL_DB_REMOVEABANDONEDTIMEOUT': '301',
        'ATL_DB_TESTONBORROW': 'true',
        'ATL_DB_TESTWHILEIDLE': 'false',
        'ATL_DB_TIMEBETWEENEVICTIONRUNSMILLIS': '30001',
        'ATL_DB_VALIDATIONQUERY': 'select 2',
    }
    container = run_image(docker_cli, image, user=run_user, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    xml = parse_xml(container, f'{get_app_home(container)}/dbconfig.xml')

    assert xml.findtext('.//database-type') == environment.get('ATL_DB_TYPE')
    assert xml.findtext('.//driver-class') == environment.get('ATL_DB_DRIVER')
    assert xml.findtext('.//url') == environment.get('ATL_JDBC_URL')
    assert xml.findtext('.//username') == environment.get('ATL_JDBC_USER')
    assert xml.findtext('.//password') == environment.get('ATL_JDBC_PASSWORD')
    assert xml.findtext('.//schema-name') == environment.get('ATL_DB_SCHEMA_NAME')
    assert xml.findtext('.//connection-properties') == 'tcpKeepAlive=false;socketTimeout=999'

    assert xml.findtext('.//pool-min-size') == environment.get('ATL_DB_POOLMINSIZE')
    assert xml.findtext('.//pool-max-size') == environment.get('ATL_DB_POOLMAXSIZE')
    assert xml.findtext('.//pool-min-idle') == environment.get('ATL_DB_MINIDLE')
    assert xml.findtext('.//pool-max-idle') == environment.get('ATL_DB_MAXIDLE')
    assert xml.findtext('.//pool-max-wait') == environment.get('ATL_DB_MAXWAITMILLIS')
    assert xml.findtext('.//validation-query') == environment.get('ATL_DB_VALIDATIONQUERY')
    assert xml.findtext('.//validation-query-timeout') is None
    assert xml.findtext('.//time-between-eviction-runs-millis') == environment.get('ATL_DB_TIMEBETWEENEVICTIONRUNSMILLIS')
    assert xml.findtext('.//min-evictable-idle-time-millis') == environment.get('ATL_DB_MINEVICTABLEIDLETIMEMILLIS')
    assert xml.findtext('.//pool-remove-abandoned') == environment.get('ATL_DB_REMOVEABANDONED')
    assert xml.findtext('.//pool-remove-abandoned-timeout') == environment.get('ATL_DB_REMOVEABANDONEDTIMEOUT')
    assert xml.findtext('.//pool-test-while-idle') == environment.get('ATL_DB_TESTWHILEIDLE')
    assert xml.findtext('.//pool-test-on-borrow') == environment.get('ATL_DB_TESTONBORROW')


def test_dbconfig_xml_params_mysql(docker_cli, image, run_user):
    environment = {
        'ATL_DB_TYPE': 'mysql8',
        'ATL_DB_DRIVER': 'com.mysql.jdbc.Driver',
        'ATL_JDBC_URL': 'jdbc:mysql://mypostgres.mycompany.org:5432/jiradb',
        'ATL_JDBC_USER': 'jiradbuser',
        'ATL_JDBC_PASSWORD': 'jiradbpassword',
        'ATL_DB_SCHEMA_NAME': 'private',
        'ATL_DB_KEEPALIVE': 'false',
        'ATL_DB_SOCKETTIMEOUT': '999',
        'ATL_DB_MAXIDLE': '21',
        'ATL_DB_MAXWAITMILLIS': '30001',
        'ATL_DB_MINEVICTABLEIDLETIMEMILLIS': '5001',
        'ATL_DB_MINIDLE': '11',
        'ATL_DB_POOLMAXSIZE': '101',
        'ATL_DB_POOLMINSIZE': '21',
        'ATL_DB_REMOVEABANDONED': 'false',
        'ATL_DB_REMOVEABANDONEDTIMEOUT': '301',
        'ATL_DB_TESTONBORROW': 'true',
        'ATL_DB_TESTWHILEIDLE': 'false',
        'ATL_DB_TIMEBETWEENEVICTIONRUNSMILLIS': '30001',
        'ATL_DB_VALIDATIONQUERY': 'select 2',
        'ATL_DB_VALIDATIONQUERYTIMEOUT': '99',
    }
    container = run_image(docker_cli, image, user=run_user, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    xml = parse_xml(container, f'{get_app_home(container)}/dbconfig.xml')

    assert xml.findtext('.//database-type') == environment.get('ATL_DB_TYPE')
    assert xml.findtext('.//driver-class') == environment.get('ATL_DB_DRIVER')
    assert xml.findtext('.//url') == environment.get('ATL_JDBC_URL')
    assert xml.findtext('.//username') == environment.get('ATL_JDBC_USER')
    assert xml.findtext('.//password') == environment.get('ATL_JDBC_PASSWORD')
    assert xml.findtext('.//schema-name') == environment.get('ATL_DB_SCHEMA_NAME')
    assert xml.findtext('.//connection-properties') is None

    assert xml.findtext('.//pool-min-size') == environment.get('ATL_DB_POOLMINSIZE')
    assert xml.findtext('.//pool-max-size') == environment.get('ATL_DB_POOLMAXSIZE')
    assert xml.findtext('.//pool-min-idle') == environment.get('ATL_DB_MINIDLE')
    assert xml.findtext('.//pool-max-idle') == environment.get('ATL_DB_MAXIDLE')
    assert xml.findtext('.//pool-max-wait') == environment.get('ATL_DB_MAXWAITMILLIS')
    assert xml.findtext('.//validation-query') == environment.get('ATL_DB_VALIDATIONQUERY')
    assert xml.findtext('.//validation-query-timeout') == environment.get('ATL_DB_VALIDATIONQUERYTIMEOUT')
    assert xml.findtext('.//time-between-eviction-runs-millis') == environment.get('ATL_DB_TIMEBETWEENEVICTIONRUNSMILLIS')
    assert xml.findtext('.//min-evictable-idle-time-millis') == environment.get('ATL_DB_MINEVICTABLEIDLETIMEMILLIS')
    assert xml.findtext('.//pool-remove-abandoned') == environment.get('ATL_DB_REMOVEABANDONED')
    assert xml.findtext('.//pool-remove-abandoned-timeout') == environment.get('ATL_DB_REMOVEABANDONEDTIMEOUT')
    assert xml.findtext('.//pool-test-while-idle') == environment.get('ATL_DB_TESTWHILEIDLE')
    assert xml.findtext('.//pool-test-on-borrow') == environment.get('ATL_DB_TESTONBORROW')


def test_cluster_properties_defaults(docker_cli, image, run_user):
    environment = {
        'CLUSTERED': 'true',
    }
    container = run_image(docker_cli, image, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    properties = parse_properties(container, f'{get_app_home(container)}/cluster.properties')
    container_id = container.file('/etc/container_id').content.decode().strip()

    assert len(container_id) > 0

    assert properties.get('jira.node.id') == container_id
    assert properties.get('jira.shared.home') == '/var/atlassian/application-data/jira/shared'
    assert properties.get('ehcache.peer.discovery') is None
    assert properties.get('ehcache.listener.hostName') is None
    assert properties.get('ehcache.listener.port') is None
    assert properties.get('ehcache.object.port') is None
    assert properties.get('ehcache.listener.socketTimeoutMillis') is None
    assert properties.get('ehcache.multicast.address') is None
    assert properties.get('ehcache.multicast.port') is None
    assert properties.get('ehcache.multicast.timeToLive') is None
    assert properties.get('ehcache.multicast.hostName') is None


def test_clustered_false(docker_cli, image, run_user):
    container = run_image(docker_cli, image)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    container.run_test(f'test -f {get_app_home(container)}/cluster.properties')


def test_cluster_properties_params(docker_cli, image, run_user):
    environment = {
        'CLUSTERED': 'true',
        'JIRA_NODE_ID': 'jiradc1',
        'JIRA_SHARED_HOME': '/data/shared',
        'EHCACHE_PEER_DISCOVERY': 'default',
        'EHCACHE_LISTENER_HOSTNAME': 'jiradc1.local',
        'EHCACHE_LISTENER_PORT': '40002',
        'EHCACHE_OBJECT_PORT': '40003',
        'EHCACHE_LISTENER_SOCKETTIMEOUTMILLIS': '2001',
        'EHCACHE_MULTICAST_ADDRESS': '1.2.3.4',
        'EHCACHE_MULTICAST_PORT': '40004',
        'EHCACHE_MULTICAST_TIMETOLIVE': '1000',
        'EHCACHE_MULTICAST_HOSTNAME': 'jiradc1.local',
    }
    container = run_image(docker_cli, image, user=run_user, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    properties = parse_properties(container, f'{get_app_home(container)}/cluster.properties')

    assert properties.get('jira.node.id') == environment.get('JIRA_NODE_ID')
    assert properties.get('jira.shared.home') == environment.get('JIRA_SHARED_HOME')
    assert properties.get('ehcache.peer.discovery') == environment.get('EHCACHE_PEER_DISCOVERY')
    assert properties.get('ehcache.listener.hostName') == environment.get('EHCACHE_LISTENER_HOSTNAME')
    assert properties.get('ehcache.listener.port') == environment.get('EHCACHE_LISTENER_PORT')
    assert properties.get('ehcache.object.port') == environment.get('EHCACHE_OBJECT_PORT')
    assert properties.get('ehcache.listener.socketTimeoutMillis') == environment.get('EHCACHE_LISTENER_SOCKETTIMEOUTMILLIS')
    assert properties.get('ehcache.multicast.address') == environment.get('EHCACHE_MULTICAST_ADDRESS')
    assert properties.get('ehcache.multicast.port') == environment.get('EHCACHE_MULTICAST_PORT')
    assert properties.get('ehcache.multicast.timeToLive') == environment.get('EHCACHE_MULTICAST_TIMETOLIVE')
    assert properties.get('ehcache.multicast.hostName') == environment.get('EHCACHE_MULTICAST_HOSTNAME')


# This test uses a dirty workaround for bitbucket docker volumes issues. It tests what we want to and it works!
def test_cluster_properties_params_overwrite(docker_cli, image, run_user):
    environment = {
        'CLUSTERED': 'true',
        'JIRA_NODE_ID': 'jiradc1',
        'JIRA_SHARED_HOME': '/data/shared',
        'EHCACHE_PEER_DISCOVERY': 'default',
        'EHCACHE_LISTENER_HOSTNAME': 'jiradc1.local',
        'EHCACHE_LISTENER_PORT': '40002',
        'EHCACHE_OBJECT_PORT': '40003',
        'EHCACHE_LISTENER_SOCKETTIMEOUTMILLIS': '2001',
        'EHCACHE_MULTICAST_ADDRESS': '1.2.3.4',
        'EHCACHE_MULTICAST_PORT': '40004',
        'EHCACHE_MULTICAST_TIMETOLIVE': '1000',
        'EHCACHE_MULTICAST_HOSTNAME': 'jiradc1.local',
    }

    placeholder_value = 'someValue'

    container = docker_cli.containers.create(image, detach=True, user=run_user, environment=environment)
    container_host = testinfra.get_host(f'docker://{container.id}')

    container.start()
    _jvm = wait_for_proc(container_host, get_bootstrap_proc(container_host))
    docker_properties_folder_path = get_app_home(container_host)

    file_contents = fr'jira.node.id={placeholder_value}\\n' \
                    fr'jira.shared.home={placeholder_value}\\n' \
                    fr'ehcache.peer.discovery={placeholder_value}\\n' \
                    fr'ehcache.listener.hostName={placeholder_value}\\n' \
                    fr'ehcache.listener.port={placeholder_value}\\n' \
                    fr'ehcache.object.port={placeholder_value}\\n' \
                    fr'ehcache.listener.socketTimeoutMillis={placeholder_value}\\n' \
                    fr'ehcache.multicast.address={placeholder_value}\\n' \
                    fr'ehcache.multicast.port={placeholder_value}\\n' \
                    fr'ehcache.multicast.timeToLive={placeholder_value}\\n' \
                    fr'ehcache.multicast.hostName={placeholder_value}'

    exit_code, output = container.exec_run(cmd=rf"sh -c 'echo {file_contents} > {docker_properties_folder_path}/cluster.properties'")
    assert exit_code == 0

    container.stop(timeout=0)

    container.start()
    _jvm = wait_for_proc(container_host, get_bootstrap_proc(container_host))
    properties = parse_properties(container_host, f'{docker_properties_folder_path}/cluster.properties')

    assert properties.get('jira.node.id') == environment.get('JIRA_NODE_ID')
    assert properties.get('jira.shared.home') == environment.get('JIRA_SHARED_HOME')
    assert properties.get('ehcache.peer.discovery') == environment.get('EHCACHE_PEER_DISCOVERY')
    assert properties.get('ehcache.listener.hostName') == environment.get('EHCACHE_LISTENER_HOSTNAME')
    assert properties.get('ehcache.listener.port') == environment.get('EHCACHE_LISTENER_PORT')
    assert properties.get('ehcache.object.port') == environment.get('EHCACHE_OBJECT_PORT')
    assert properties.get('ehcache.listener.socketTimeoutMillis') == environment.get('EHCACHE_LISTENER_SOCKETTIMEOUTMILLIS')
    assert properties.get('ehcache.multicast.address') == environment.get('EHCACHE_MULTICAST_ADDRESS')
    assert properties.get('ehcache.multicast.port') == environment.get('EHCACHE_MULTICAST_PORT')
    assert properties.get('ehcache.multicast.timeToLive') == environment.get('EHCACHE_MULTICAST_TIMETOLIVE')
    assert properties.get('ehcache.multicast.hostName') == environment.get('EHCACHE_MULTICAST_HOSTNAME')


def test_jvm_args(docker_cli, image, run_user):
    environment = {
        'JVM_MINIMUM_MEMORY': '383m',
        'JVM_MAXIMUM_MEMORY': '2047m',
        'JVM_RESERVED_CODE_CACHE_SIZE': '383m',
        'JVM_SUPPORT_RECOMMENDED_ARGS': '-verbose:gc',
    }
    container = run_image(docker_cli, image, user=run_user, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    procs_list = get_procs(container)
    jvm = [proc for proc in procs_list if get_bootstrap_proc(container) in proc][0]

    assert f'-Xms{environment.get("JVM_MINIMUM_MEMORY")}' in jvm
    assert f'-Xmx{environment.get("JVM_MAXIMUM_MEMORY")}' in jvm
    assert f'-XX:ReservedCodeCacheSize={environment.get("JVM_RESERVED_CODE_CACHE_SIZE")}' in jvm
    assert environment.get('JVM_SUPPORT_RECOMMENDED_ARGS') in jvm


def test_first_run_state(docker_cli, image, run_user):
    container = run_image(docker_cli, image, user=run_user, ports={PORT: PORT})

    wait_for_http_response(STATUS_URL, expected_status=200, expected_state=('STARTING', 'FIRST_RUN'))


def test_clean_shutdown(docker_cli, image, run_user):
    container = docker_cli.containers.run(image, detach=True, user=run_user, ports={PORT: PORT})
    host = testinfra.get_host("docker://"+container.id)
    wait_for_state(STATUS_URL, expected_state='FIRST_RUN')

    container.kill(signal.SIGTERM)

    end = r'org\.apache\.coyote\.AbstractProtocol\.destroy Destroying ProtocolHandler'
    wait_for_log(container, end)


def test_shutdown_script(docker_cli, image, run_user):
    container = docker_cli.containers.run(image, detach=True, user=run_user, ports={PORT: PORT})
    host = testinfra.get_host("docker://"+container.id)
    wait_for_state(STATUS_URL, expected_state='FIRST_RUN')

    container.exec_run('/shutdown-wait.sh')

    end = r'org\.apache\.coyote\.AbstractProtocol\.destroy Destroying ProtocolHandler'
    wait_for_log(container, end)


def test_java_in_user_path(docker_cli, image):
    container = run_image(docker_cli, image)
    proc = container.check_output('su -c "which java" ${RUN_USER}')
    assert len(proc) > 0


def test_seraph_xml_defaults(docker_cli, image):
    container = run_image(docker_cli, image)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    xml = parse_xml(container, f'{get_app_install_dir(container)}/atlassian-jira/WEB-INF/classes/seraph-config.xml')
    assert [el.findtext('.//param-value') for el in xml.findall('.//init-param')
            if el.findtext('.//param-name') == 'autologin.cookie.age'][0] == '1209600'


def test_seraph_xml_params(docker_cli, image):
    environment = {'ATL_AUTOLOGIN_COOKIE_AGE': '9001'}
    container = run_image(docker_cli, image, environment=environment)
    _jvm = wait_for_proc(container, get_bootstrap_proc(container))

    xml = parse_xml(container, f'{get_app_install_dir(container)}/atlassian-jira/WEB-INF/classes/seraph-config.xml')
    assert [el.findtext('.//param-value') for el in xml.findall('.//init-param')
            if el.findtext('.//param-name') == 'autologin.cookie.age'][0] == environment.get('ATL_AUTOLOGIN_COOKIE_AGE')


def test_dbconfig_xml_no_overwrite(docker_cli, image, run_user):
    environment = {
        'ATL_DB_TYPE': 'postgres72',
        'ATL_DB_DRIVER': 'org.postgresql.Driver',
        'ATL_JDBC_URL': 'jdbc:postgresql://mypostgres.mycompany.org:5432/jiradb',
        'ATL_JDBC_USER': 'jiradbuser',
        'ATL_JDBC_PASSWORD': 'jiradbpassword',
    }

    container = docker_cli.containers.run(image, detach=True, user=run_user, environment=environment)
    tihost = testinfra.get_host("docker://"+container.id)
    _jvm = wait_for_proc(tihost, get_bootstrap_proc(tihost))
    cfg = f'{get_app_home(tihost)}/dbconfig.xml'

    xml = parse_xml(tihost, cfg)
    assert xml.findtext('.//jdbc-datasource/username') == 'jiradbuser'

    container.exec_run(f"sed -i 's/jiradbuser/differentuser/' {cfg}")

    xml = parse_xml(tihost, cfg)
    assert xml.findtext('.//jdbc-datasource/username') == 'differentuser'

    container.stop(timeout=60)
    container.start()
    _jvm = wait_for_proc(tihost, get_bootstrap_proc(tihost))

    xml = parse_xml(tihost, cfg)
    assert xml.findtext('.//jdbc-datasource/username') == 'differentuser'


def test_dbconfig_xml_force_overwrite(docker_cli, image, run_user):
    environment = {
        'ATL_DB_TYPE': 'postgres72',
        'ATL_DB_DRIVER': 'org.postgresql.Driver',
        'ATL_JDBC_URL': 'jdbc:postgresql://mypostgres.mycompany.org:5432/jiradb',
        'ATL_JDBC_USER': 'jiradbuser',
        'ATL_JDBC_PASSWORD': 'jiradbpassword',
        'ATL_FORCE_CFG_UPDATE': 'y',
    }

    container = docker_cli.containers.run(image, detach=True, user=run_user, environment=environment)
    tihost = testinfra.get_host("docker://"+container.id)
    _jvm = wait_for_proc(tihost, get_bootstrap_proc(tihost))
    cfg = f'{get_app_home(tihost)}/dbconfig.xml'

    xml = parse_xml(tihost, cfg)
    assert xml.findtext('.//jdbc-datasource/username') == 'jiradbuser'

    container.exec_run(f"sed -i 's/jiradbuser/differentuser/' {cfg}")

    xml = parse_xml(tihost, cfg)
    assert xml.findtext('.//jdbc-datasource/username') == 'differentuser'

    container.stop(timeout=60)
    container.start()
    _jvm = wait_for_proc(tihost, get_bootstrap_proc(tihost))

    xml = parse_xml(tihost, cfg)
    assert xml.findtext('.//jdbc-datasource/username') == 'jiradbuser'

