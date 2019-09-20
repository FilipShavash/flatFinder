import re, socket, urllib.request, urllib.parse, urllib.error
from lxml import html
from Utils import Utils
import time, os
from random import randint
import json, datetime
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class FlatFinder:
    def __init__(self):
        # flats from the following districts are to be ignored
        self.blacklist = ['Białołęka', 'Wilanów', 'Wesoła', 'Wawer', 'Ursus', 'Rembertów', 'Tarchomin', 'Bródno', 'Bemowo', 'Włochy']
        # blacklist for gumtree spammers
        self.gumtree_banned_users = ['v1u104723556p1', 'v1u114062620p1', 'v1u106631557p1', 'v1u114307443p1',
                                     'v1u104708683p1', 'v1u110031518p1', 'v1u112951387p1', 'v1u112279346p1',
                                     'v1u112589486p1', 'v1u104758381p1', 'v1u104714794p1', 'v1u109432260p1',
                                     'v1u104747383p1', 'v1u113773662p1', 'v1u106273094p1', 'v1u108900708p1',
                                     'v1u112799929p1', 'v1u113446522p1', 'v1u113932676p1', 'v1u113729863p1',
                                     'v1u111780756p1', 'v1u114087830p1', 'v1u114097713p1', 'v1u104729696p1',
                                     'v1u104780607p1', 'v1u104780607p1', 'v1u104740910p1', 'v1u104686003p1',
                                     'v1u104765304p1', 'v1u114677170p1', 'v1u113405180p1', 'v1u117645552p1',
                                     'v1u123901501p1', 'v1u123905547p1', 'v1u112446767p1', 'v1u105050789p1',
                                     'v1u121059903p1', 'v1u113627808p1']
        # Google API key
        self.api_key = os.environ['API_KEY']
        self.city_name = 'Warszawa'
        self.gumtree_min_flat_size = 30

        self.headers = {'User-Agent': "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:48.0) Gecko/20100101 Firefox/48.0"}
        self.flats = []

    def get_flats_gumtree(self, filename, url, id_gumtree_filename, search_type='flat', min_flat_size=40):
        # minimal size of the flat in m^2 (apply only to gumtree)
        self.gumtree_min_flat_size = min_flat_size
        try:
            self.id_gumtree = Utils.read_json_file(id_gumtree_filename)
        except FileNotFoundError:
            self.id_gumtree = []
        try:
            os.rename('{}_geo.json'.format(filename),
                      '{}_{}.json'.format(filename, datetime.datetime.now().strftime("%Y-%m-%d")))
        except FileNotFoundError:
            pass
        self.flats = []
        url_base = 'https://www.gumtree.pl'

        # for index, url_page in enumerate(pages):
        for page_num in range(1,25):
            print('Page: ' + str(page_num))
            end_cond = True
            url_page = url_base+url.replace('p1', 'p'+str(page_num), 1)
            html_page = self.safe_call(url_page)
            offers = html_page.xpath('//div[@class="view"]/div[@class="tileV1"]')
            for offer in offers:
                flat = {'id': offer.xpath('.//div[@class="reply-action"]/div')[0].attrib['data-short-id']}
                if flat['id'] in self.id_gumtree:
                    self.id_gumtree.append(flat['id'])
                    continue
                self.id_gumtree.append(flat['id'])
                end_cond = False
                title_elem = offer.xpath('.//div[@class="title"]/a')[0]
                flat['link'] = url_base + title_elem.attrib['href']
                flat['title'] = title_elem.text
                print(flat['link'])
                if search_type == 'garage':
                    flat = self.process_gumtree_garage(flat)
                else:
                    flat = self.process_gumtree(flat)
                # skip this offer if it's from blacklisted discrict
                if not flat or self.blacklisted_discrict(flat['district']):
                    continue
                if not flat['address']:
                    flat['address'] = self.find_address(flat['title'])
                print(
                    '{} {}    |    {}    |    {}'.format(flat['id'], flat['district'], flat['address'], flat['title']))
                self.flats.append(flat)
            if end_cond:
                break
        self.flats = sorted(self.flats, key=lambda k: (k['id']))
        Utils.deleteDuplicates(self.flats)
        Utils.save_json_file('{}.json'.format(filename), self.flats)
        sorted(self.id_gumtree)
        Utils.save_json_file(id_gumtree_filename, self.id_gumtree)

    def get_flats_olx(self, filename, url, id_olx_filename):
        try:
            self.id_olx = Utils.read_json_file(id_olx_filename)
        except FileNotFoundError:
            self.id_olx = []
        try:
            os.rename('{}_geo.json'.format(filename),
                      '{}_geo_{}.json'.format(filename, datetime.datetime.now().strftime("%Y-%m-%d")))
        except FileNotFoundError:
            pass
        self.flats = []
        url = 'https://www.olx.pl' + url
        html_page = self.safe_call(url)
        # get number of pages to search
        try:
            pages = str(html_page.xpath('//div[@class="pager rel clr"]')[0].text_content()).strip()
            number = re.findall(r'.+(\d)', pages, re.DOTALL)[0]
        except IndexError:
            number = 1

        for page in range(0, int(number)):
            url_page = url + '&page=' + str(page + 1)
            html_page = self.safe_call(url_page)
            offers = html_page.xpath('//table[@id="offers_table"]/tbody/tr/td[contains(@class,"offer")]')
            for offer in offers:
                flat = {}
                try:
                    flat['id'] = offer.xpath('.//table')[0].attrib['data-id']
                    if flat['id'] in self.id_olx:
                        self.id_olx.append(flat['id'])
                        continue
                except Exception:
                    continue
                self.id_olx.append(flat['id'])
                a_elem = offer.xpath('.//a')[1]
                flat['link'] = a_elem.attrib['href']
                print(flat['link'])
                flat['title'] = str(a_elem.text_content()).strip()
                p_elems = offer.xpath('.//tr[2]//p//span')
                # find discrict
                flat['district'] = str(p_elems[0].text_content()).strip()
                # find an address
                if 'olx.pl' in flat['link']:
                    flat['address'] = self.process_olx(flat['title'], flat['link'], flat['district'])
                else:
                    flat['address'] = self.process_otodom(flat['title'], flat['link'], flat['district'])
                # skip this offer if it's from blacklisted discrict
                if self.blacklisted_discrict(flat['district']):
                    continue
                # delete multi-spaces
                if flat['address']:
                    flat['address'] = re.sub(' +', ' ', flat['address'])
                    flat['address'] = self.replace_rules(flat['address'])
                print(
                    '{} {}    |    {}    |    {}'.format(flat['id'], flat['district'], flat['address'], flat['title']))
                self.flats.append(flat)
        self.flats = sorted(self.flats, key=lambda k: (k['id']))
        Utils.deleteDuplicates(self.flats)
        Utils.save_json_file('{}.json'.format(filename), self.flats)
        sorted(self.id_olx)
        Utils.save_json_file(id_olx_filename, self.id_olx)

    def process_olx(self, title, url, district):
        address = self.find_address(title)
        if address:
            return '{}, {}'.format(district, address)
        html_page = self.safe_call(url)
        description = str(html_page.xpath(r'//div[@id="textContent"]')[0].text_content())
        # garage check
        # if not self.find_garage(description):
        #    return None
        address = self.find_address(description)
        if address:
            return '{}, {}'.format(district, address)
        return None

    def process_otodom(self, title, url, district):
        html_page = self.safe_call(url)
        # garage_tab = html_page.xpath(r'//ul[@class="dotted-list"]')
        # check for garage
        # test = str(garage_tab[-1].text_content()).strip()
        # res = test.find('garaż/miejsce parkingowe')
        # if res:
        #     pass
        # if not (len(garage_tab) > 1 and not str(garage_tab[-1].text_content()).find('garaż/miejsce parkingowe')):
        #    return None
        try:
            try:
                json_elem = html_page.xpath('//script[@id="server-app-state"]')
                json_content = json.loads(json_elem[0].text_content())
                address = json_content['initialProps']['data']['advert']['breadcrumb'][-1]['label']
                to_remove = district.split(',')
                for rem in to_remove:
                    address = address.replace(rem.strip(), '')
                if len(address.strip()) > 0:
                    return '{}, {}'.format(district, address)
            except Exception:
                pass
            address = html_page.xpath('//a[contains(@href, "street_id")]')
            if address:
                address = address[0].text_content()
            else:
                descr = html_page.xpath('//section[@class="section-description"]')[0].text_content()
                address = self.find_address(descr)
            if address:
                return '{}, {}'.format(district, address)
            # address = str(html_page.xpath(r'//p[@class="address-links"]')[0].text_content())
            # return address[address.find(self.city_name):address.rfind('-')]
        except IndexError:
            return None

    def process_gumtree_garage(self, flat_struct):
        html_page = self.safe_call(flat_struct['link'])
        userid = html_page.xpath('//span[@class="username"]/a/@href')[0]
        userid = userid[userid.rfind('/') + 1:]
        if self.banned_user(userid):
            return None
        flat_struct['district'] = re.sub(r'\s{2,}', '',
                                         str(html_page.xpath('//div[@class="location"]')[1].text_content()))
        flat_struct['address'] = html_page.xpath('//h5[@class="full-address"]/span[@class="address"]')[0].text
        if ',' in flat_struct['address']:
            # remove postcode
            result = re.findall(r'\d{2}-\d{3}', flat_struct['address'])
            if len(result) > 0:
                flat_struct['address'] = flat_struct['address'].replace(result[0], '')
            return flat_struct
        description = str(html_page.xpath('//div[@class="description"]')[0].text_content())
        flat_struct['address'] = self.find_address(description)
        if flat_struct['address']:
            flat_struct['address'] = '{}, {}'.format(flat_struct['district'], flat_struct['address'])
        return flat_struct

    def process_gumtree(self, flat_struct):
        html_page = self.safe_call(flat_struct['link'])
        try:
            flat_size = \
                html_page.xpath('//div[@class="attribute"]/span[text()="Wielkość (m2)"]/following-sibling::span')[
                    0].text
            if int(flat_size) < self.gumtree_min_flat_size:
                return None
            room_num = html_page.xpath('//div[@class="attribute"]/span[text()="Liczba pokoi"]/following-sibling::span')[
                0].text
            if not any(char.isdigit() for char in room_num):
                return None
            flat_struct['address'] = html_page.xpath('//h5[@class="full-address"]/span[@class="address"]')[0].text
        except IndexError:
            return None
        userid = html_page.xpath('//span[@class="username"]/a/@href')[0]
        userid = userid[userid.rfind('/') + 1:]
        if self.banned_user(userid):
            return None
        flat_struct['district'] = re.sub(r'\s{2,}', '',
                                         str(html_page.xpath('//div[@class="location"]')[1].text_content()))
        remove_part = flat_struct['district'].split(',')
        for rem in remove_part:
            flat_struct['address'] = flat_struct['address'].replace(rem.strip(), '')
        flat_struct['address'] = flat_struct['address'].replace(',', '')
        # remove postcode
        result = re.findall(r'\d{2}-\d{3}', flat_struct['address'])
        if len(result) > 0:
            flat_struct['address'] = flat_struct['address'].replace(result[0], '')
        if len(flat_struct['address'].strip()) > 0:
            flat_struct['address'] = '{}, {}'.format(flat_struct['district'], flat_struct['address'])
            return flat_struct
        description = str(html_page.xpath('//div[@class="description"]')[0].text_content())
        flat_struct['address'] = self.find_address(description)
        if flat_struct['address']:
            flat_struct['address'] = '{}, {}'.format(flat_struct['district'], flat_struct['address'])
        return flat_struct

    def find_garage(self, text):
        garage = re.findall(r'[Gg]araż|[Mm]iejsc[eau]m?\spostojow', text)
        if len(garage) > 0:
            return True
        else:
            return False

    def find_address(self, text):
        address = re.findall(
            r'[uU]l(?:ica|icy){0,1}\.{0,1}\s{0,1}([A-ZŚŻŹŁĆŃ](?:\w{1,2}\.|\w+)(?:-{0,1}\s{0,1}[A-ZŚŻŹŁĆŃ]\w+)*\s{0,1}\d{0,4})',
            text)
        if len(address) > 0:
            return address[0]
        return None

    def blacklisted_discrict(self, district):
        for item in self.blacklist:
            if item in district:
                return True
        return False

    def banned_user(self, user):
        if user in self.gumtree_banned_users:
            return True
        return False

    def safe_call(self, url, geo=None):
        done = False
        content = None
        while not done:
            try:
                request = urllib.request.Request(url, headers=self.headers)
                response = urllib.request.urlopen(request, timeout=20)
                resp_code = int(str(response.code)[0])
                if resp_code != 2:
                    print('Error returned {} for URL: {}'.format(response.code, url))
                    time.sleep(2)
                    continue
            except urllib.error.HTTPError:
                print('Error returned for URL: {}'.format(url))
                time.sleep(2)
                continue
            except urllib.error.URLError:
                print('Timeout')
                continue
            except socket.timeout:
                print('Timeout')
                continue
            try:
                content = response.read()
            except socket.timeout:
                print('Timeout')
                continue
            done = True
        if not geo:
            return html.fromstring(content)
        else:
            return content

    def get_geolocalization(self, filename_src, filename_target):
        self.flats = Utils.read_json_file(filename_src)
        url_base = 'https://maps.googleapis.com/maps/api/geocode/json?key={}&region=pl&address='.format(self.api_key)
        for flat in self.flats:
            if not flat['address']:                continue
            if self.has_digit(flat['address']):
                flat['precise'] = True
            else:
                flat['precise'] = False
            address = urllib.parse.quote_plus(flat['address'].strip())
            url = url_base + address
            print('{} {} {}'.format(flat['link'], flat['address'], url))
            # response = urllib.request.urlopen(url)
            response = self.safe_call(url, True)
            resp_json = json.loads(response)
            latitude = resp_json['results'][0]['geometry']['location']['lat']
            longitude = resp_json['results'][0]['geometry']['location']['lng']
            if not flat['precise']:
                latitude = latitude + randint(0, 10) * 0.0001
                longitude = longitude + randint(0, 10) * 0.0001
            flat['latitude'] = latitude
            flat['longitude'] = longitude
        Utils.save_json_file(filename_target, self.flats)

    def has_digit(self, text):
        return any(char.isdigit() for char in text)

    def print_uknown(self, filename):
        print('\nPrinting flats with uknown location for {}:'.format(filename))
        self.flats = Utils.read_json_file(filename)
        for flat in self.flats:
            if flat['address']:
                continue
            print('{} {} {}'.format(flat['title'], flat['link'], flat['district']))

    def prepare_id_tab(self):
        self.flats = Utils.read_json_file('flats_olx_geo.json')
        ids = []
        for flat in self.flats:
            ids.append(flat['id'])
        sorted(ids)
        Utils.save_json_file(self.id_olx_filename, ids)

    def replace_rules(self, text):
        text = text.replace('Dolny Mokotów', 'Mokotów')
        text = text.replace('Górny Mokotów', 'Mokotów')
        return text

    def send_email(self, file1, file2, file3, file4):
        content1 = Utils.read_json_file(file1)
        content2 = Utils.read_json_file(file2)
        content3 = Utils.read_json_file(file3)
        content4 = Utils.read_json_file(file4)
        if not content1 and not content2 and not content3 and not content4:
            print("Nothing to send!")
            return


        date_formatted = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        smtp_server = "smtp.gmail.com"
        port = 465
        sender_email = "decapromolist@gmail.com"
        receiver_email = os.environ['EMAIL_RECEIVER']
        password = os.environ['EMAIL_PASSWORD']

        message = MIMEMultipart("alternative")
        message["Subject"] = "Mieszkania z dn. {}".format(date_formatted)
        message["From"] = sender_email
        message["To"] = receiver_email
        receiver_emails = receiver_email.split(',')

        url_flats1 = 'https://thof.github.io/draw_map.html?key={}&list={}&list={}'.format(self.api_key, file1, file2)
        url_flats2 = 'https://thof.github.io/draw_map.html?key={}&list={}&list={}'.format(self.api_key, file3, file4)
        url_flats3 = 'https://thof.github.io/print_unknown.html?list={}&list={}'.format(file1, file2)
        url_flats4 = 'https://thof.github.io/print_unknown.html?list={}&list={}'.format(file3, file4)

        html = """\
        <html>
          <body>
            <p>Mieszkania z dn. {}</p>
            <p>
        """.format(date_formatted)
        if [True for elem in content1 if elem['address']] or [True for elem in content2 if elem['address']]:
            html = """{}\
                <a href="{}">Mapa mieszkań</a><br>
            """.format(html, url_flats1)
        if [True for elem in content1 if not elem['address']] or [True for elem in content2 if not elem['address']]:
            html = """{}\
                <a href= "{}">Mieszkania bez lokalizacji</a>
            """.format(html, url_flats3)

        html = "{}</p><p>".format(html)
        if [True for elem in content3 if elem['address']] or [True for elem in content4 if elem['address']]:
            html = """{}\
                <a href="{}">Mapa kawalerek</a><br>
                """.format(html, url_flats2)
        if [True for elem in content3 if not elem['address']] or [True for elem in content4 if not elem['address']]:
            html = """{}\
                <a href= "{}">Kawalerki bez lokalizacji</a>
                """.format(html, url_flats4)
        html = """{}\
            </p>
          </body>
        </html>""".format(html)
        message.attach(MIMEText(html, "html"))

        # Try to log in to server and send email
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_emails, message.as_string())


if __name__ == "__main__":
    flat = FlatFinder()
    # flat.process_otodom('test', 'https://www.otodom.pl/oferta/bezposrednio-ochota-wlochy-2-pok-38m2-ID40xbC.html?', 'Warszawa, Praga-Północ')
    # flat_struct = {'link': 'https://www.gumtree.pl/a-mieszkania-i-domy-sprzedam-i-kupie/praga-poludnie/bezposrednio-od-wlasciciela-+-przestronne-mieszkanie-2-pietro-niedaleko-ronda-wiatraczna/1005021510280911545163909'}
    # flat.process_gumtree(flat_struct)

    today_date = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
    flats_gumtree_geo = 'flats_gumtree_geo_{}.json'.format(today_date)
    flats_olx_geo = 'flats_olx_geo_{}.json'.format(today_date)
    flats_kaw_gumtree_geo = 'flats_kaw_gumtree_geo_{}.json'.format(today_date)
    flats_kaw_olx_geo = 'flats_kaw_olx_geo_{}.json'.format(today_date)
    flats_kaw_olx_geo = 'flats_kaw_olx_geo_{}.json'.format(today_date)

    print('\nChecking gumtree:')
    flat.get_flats_gumtree('flats_gumtree',
                           '/s-mieszkania-i-domy-sprzedam-i-kupie/warszawa/v1c9073l3200008p1?df=ownr&pr=,450000&sort=dt&order=desc', 'id_gumtree.json',  min_flat_size=38)
#    flat.get_geolocalization('flats_gumtree.json', flats_gumtree_geo)
    print('\nChecking olx:')
    flat.get_flats_olx('flats_olx',
                       '/nieruchomosci/mieszkania/sprzedaz/warszawa/?search%5Bfilter_float_price%3Ato%5D=450000&search%5Bfilter_float_m%3Afrom%5D=38&search%5Bfilter_enum_rooms%5D%5B0%5D=two&search%5Bfilter_enum_rooms%5D%5B1%5D=three&search%5Bfilter_enum_rooms%5D%5B2%5D=four&search%5Bphotos%5D=1&search%5Bprivate_business%5D=private&search%5Border%5D=created_at%3Adesc', 'id_olx.json')
#    flat.get_geolocalization('flats_olx.json', flats_olx_geo)

    print('\nKawalerki Checking gumtree:')
    flat.get_flats_gumtree('flats_kaw_gumtree',
                           '/s-mieszkania-i-domy-sprzedam-i-kupie/warszawa/v1c9073l3200008p1?df=ownr&pr=,330000&nr=10&sort=dt&order=desc',
                           'id_kaw_gumtree.json', min_flat_size=29)
#    flat.get_geolocalization('flats_kaw_gumtree.json', flats_kaw_gumtree_geo)
    print('\nKawalerki Checking olx:')
    flat.get_flats_olx('fla'
                       'ts_kaw_olx',
                       '/nieruchomosci/mieszkania/sprzedaz/warszawa/?search[filter_float_price%3Ato]=330000&search[filter_float_m%3Afrom]=29&search[filter_enum_rooms][0]=one&search[photos]=1&search[private_business]=private&search[order]=created_at%3Adesc',
                       'id_kaw_olx.json')
#    flat.get_geolocalization('flats_kaw_olx.json', flats_kaw_olx_geo)

    # print flats where the geolocation is unknown
    flat.print_uknown(flats_olx_geo)
    flat.print_uknown(flats_gumtree_geo)

    # print flats where the geolocation is unknown
    flat.print_uknown(flats_kaw_olx_geo)
    flat.print_uknown(flats_kaw_gumtree_geo)

    flat.send_email(flats_gumtree_geo, flats_olx_geo, flats_kaw_gumtree_geo, flats_kaw_olx_geo)


    # flats to 450 000
    # print('\nChecking 450 gumtree:')
    # flat.get_flats_gumtree('flats_450_gumtree',
    #                        '/s-mieszkania-i-domy-sprzedam-i-kupie/warszawa/v1c9073l3200008p1?df=ownr&pr=420000,450000&sort=dt&order=desc',
    #                        'id_450_gumtree.json', min_flat_size=39)
    # flat.get_geolocalization('flats_450_gumtree.json', 'flats_450_gumtree_geo.json')
    # print('Checking 450 olx:')
    # flat.get_flats_olx('flats_450_olx',
    #                    '/nieruchomosci/mieszkania/sprzedaz/warszawa/?search%5Bfilter_float_price%3Ato%5D=450000&search%5Bfilter_float_price%3Afrom%5D=420000&search%5Bfilter_enum_market%5D%5B0%5D=secondary&search%5Bfilter_float_m%3Afrom%5D=38&search%5Bfilter_enum_rooms%5D%5B0%5D=four&search%5Bfilter_enum_rooms%5D%5B1%5D=three&search%5Bfilter_enum_rooms%5D%5B2%5D=two&search%5Bphotos%5D=1&search%5Bprivate_business%5D=private&search%5Border%5D=created_at%3Adesc',
    #                    'id_450_olx.json')
    # flat.get_geolocalization('flats_450_olx.json', 'flats_450_olx_geo.json')
    # print flats where the geolocation in unknown
    # flat.print_uknown('flats_450_olx_geo.json')
    # flat.print_uknown('flats_450_gumtree_geo.json')

    # print('\nChecking gumtree garages:')
    # flat.get_flats_gumtree('garage1_gumtree',
    #                        '/s-parking-i-garaz/mokotow/v1c9071l3200012p1', 'garage')
    # flat.get_geolocalization('garage1_gumtree.json', 'garage1_gumtree_geo.json')
    # flat.print_uknown('garage1_gumtree_geo.json')

    # flat.get_flats_gumtree('garage_gumtree',
    #                        '/s-parking-i-garaz/ursynow/v1c9071l3200020p1', 'garage')
    # flat.get_geolocalization('garage_gumtree.json', 'garage_gumtree_geo.json')
    # flat.print_uknown('garage_gumtree_geo.json')

    # print('\nChecking gumtree garages:')
    # flat.get_flats_gumtree('garage2_gumtree',
    #                        '/s-parking-i-garaz/wola/v1c9071l3200025p1', 'garage')
    # flat.get_geolocalization('garage2_gumtree.json', 'garage2_gumtree_geo.json')
    # flat.print_uknown('garage2_gumtree_geo.json')

    # flat.prepare_id_tab()
