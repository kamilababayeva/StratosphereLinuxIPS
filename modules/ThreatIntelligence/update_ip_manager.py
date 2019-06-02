import configparser
import time
import urllib.request
from log_file_manager import __log_file_manager__
from progress_bar import ProgressBar


class UpdateIPManager:

    def __init__(self, outputqueue):
        self.outputqueue = outputqueue
        self.url_to_malicious_ips = 'https://raw.githubusercontent.com/frenky-strasak/StratosphereLinuxIPS/frenky_develop/modules/ThreatInteligence/malicious_ips_files/malicious_ips.txt'
        self.path_to_thret_intelligence_data = 'modules/ThreatIntelligence/malicious_ips_files/malicious_ips.txt'

        self.section_name = 'threat_inteligence_module'
        self.e_tag_var = 'e_tag_of_last_malicious_ip_file'
        self.last_update_var = 'threat_intelligence_ips_last_update'

        self.set_last_update = None
        self.set_e_tag = None

        self.progress_bar = ProgressBar(bar_size=10, prefix="\t\t[ThreadIntelligence] Updating: ")

    def __check_if_update(self, update_period: float) -> bool:
        """
        Check if user wants to update.
        """
        # Log file exists from last running of slips.
        try:
            last_update = float(__log_file_manager__.read_data(self.section_name, self.last_update_var))
        except TypeError:
            last_update = None

        now = time.time()
        if last_update is None:
            # We have no information about last update. Try to update.
            self.set_last_update = now
            return True
        elif last_update + update_period < now:
            # Update.
            self.set_last_update = now
            return True
        return False

    def __check_conn(self, host: str) -> bool:
        try:
            urllib.request.urlopen(host)
            return True
        except:
            return False

    def __get_e_tag_from_web(self) -> str:
        try:
            request = urllib.request.Request(self.url_to_malicious_ips)
            res = urllib.request.urlopen(request)
            e_tag = res.info().get('Etag', None)
            self.set_e_tag = e_tag
        except:
            e_tag = None
        return e_tag

    def __download_file(self, url: str, path: str) -> bool:
        # Download file from github
        try:
            urllib.request.urlretrieve(url, path)
        except:
            self.outputqueue.put('01|ThreadInteligence|[ThreadIntelligence] An error occurred during updating Threat intelligence module.')
            return False
        return True

    def __download_malicious_ips(self) -> bool:
        # check internet connection.
        tested_url = 'https://github.com/'
        internet_conn = self.__check_conn(tested_url)

        if internet_conn is False:
            self.outputqueue.put('01|ThreadIntelligence|[ThreadIntelligence] We can not connect to {}. Check your connection. Downloading of data for Threat intelligence module is aborted.'
                                 ''.format(tested_url))
            return False

        # Take last e-tag of our maliciou ips file.
        old_e_tag = __log_file_manager__.read_data(self.section_name, self.e_tag_var)
        # Check now if E-TAG of file in github is same as downloaded file here.
        new_e_tag = self.__get_e_tag_from_web()
        if old_e_tag is not None and new_e_tag is not None:
            if old_e_tag != new_e_tag:
                # Our malicious file is old. Download new one.
                self.__download_file(self.url_to_malicious_ips, self.path_to_thret_intelligence_data)

        if old_e_tag is None and new_e_tag is not None:
            # We have no information about last e-tag. Download new one.
            self.__download_file(self.url_to_malicious_ips, self.path_to_thret_intelligence_data)

        if new_e_tag is None:
            # We can not get information about e-tag. Abort downloading.
            self.outputqueue.put(
                '01|ThreadIntelligence|[ThreadIntelligence] Downloading of data for Threat intelligence module is aborted. We do not have access to {}.'
                ''.format(self.url_to_malicious_ips))
            return False
        return True

    def __set_log_file(self, variable_name: str, value: str):
        """
        Set data in slips_log.conf file.
        """
        __log_file_manager__.set_data(self.section_name, variable_name, value)

    def update(self, update_period) -> bool:

        try:
            update_period = float(update_period)
        except (TypeError, ValueError):
            # User does not want to update the malicious IP list.
            self.outputqueue.put('01|ThreadIntelligence|\t\t[ThreadIntelligence] Updating is not alowed.')
            return False

        if update_period <= 0:
            # User does not want to update the malicious IP list.
            self.outputqueue.put('01|ThreadIntelligence|\t\t[ThreadIntelligence] Updating is not alowed.')
            return False

        if self.__check_if_update(update_period):
            done = self.__download_malicious_ips()
            if done:
                self.outputqueue.put('01|ThreadIntelligence|\t\t[ThreadIntelligence] Updating was successful.')
            else:
                self.outputqueue.put(
                    '01|ThreadIntelligence|[ThreadIntelligence] An error occured during downloading data for Threat intelligence module.'
                    ' Updating was aborted.')
        else:
            self.outputqueue.put('01|ThreadIntelligence|\t\t[ThreadIntelligence] Thread Intelligence module is up to date. No downloading.')

        # Save e-tag and lastUpdate to log file if they are not None.
        if self.set_e_tag:
            self.__set_log_file(self.e_tag_var, str(self.set_e_tag))
        if self.set_last_update:
            self.__set_log_file(self.last_update_var, str(self.set_last_update))