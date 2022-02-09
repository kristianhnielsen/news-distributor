import re

class Media:
    def __init__(self, media_name, root_link=None):
        self.media_name = media_name
        self.root_link = root_link
        self.categories = []
        self.main_container = []
        self.articles = []
        self.links = []
        self.temp_data = []

    def get_articles(self):
        return self.articles

    def get_media_name(self):
        return self.media_name

    def get_links(self):
        return self.links

    def remove_duplicate_links(self):
        unique = []
        for element in self.get_links():
            if element not in unique:
                unique.append(element)
        self.links = unique

    def sort_by_date(self):
        # reverse = None (Sorts in Ascending order)
        # key is set to sort using second element of
        # sublist lambda has been used
        self.articles.sort(key=lambda article: article.publishing_date, reverse=True)


class Article(Media):
    def __init__(self, source: str):
        self.headline = ''
        self.text_body = ''
        self.publishing_date = ''
        self.source = source

    def has_content(self):
        if self.headline != None and self.headline != '':
            if self.text_body != None and self.text_body != '':
                if self.publishing_date != None and self.publishing_date != '':
                    return True
        return False

    def remove_patterns(text, regex):
            if re.search(regex, text) is not None:
                text = re.sub(regex, '', text).strip()
                return text
            else:
                return text

    def fix_binary(self):
        binary_dict = {
            b'\xc3\xa2\xc2\x80\xc2\x98': b"'",
            b'\xc3\xa2\xc2\x80\xc2\x99': b"'",
            b'\xc3\xa2\xc2\x80\xc2\x9c': b'"',
            b'\xc3\xa2\xc2\x80\xc2\x9d': b'"',
            b'\xc2\xa0': b' ',
            b'\xc3\xa2\xc2\x80\xc2\x94': b'\n',
            b'\xc3\xa2\xc2\x80\xc2\x93': b'-',
            b'\xc3\xa2\xc2\x80\xc2\xa6': b'...',
            b'\xe2\x80\x94': b'-',
            b'\xc3\xb8': b'lower_oe_replacement',
            b'\xc3\xa6': b'lower_ae_replacement',
            b'\xc3\x83\xc2\xbc': b'u_umlaut_replacement',
            b'\xc3\x85\xc2\x8d': b'o_umlaut_replacement'
        }

        non_ascii_dict = {
            'lower_ae_replacement': 'æ',
            'Ã¦': 'æ',
            'Ã¥': 'å',
            'Ã¸': 'ø',
            'lower_oe_replacement': 'ø',
            'u_umlaut_replacement': 'ü',
            'o_umlaut_replacement': 'ö'
        }

        self.text_body = self.text_body.encode('utf-8')
        self.headline = self.headline.encode('utf-8')
        for key in binary_dict.keys():
            self.text_body = self.text_body.replace(key, binary_dict.get(key))
            self.headline = self.headline.replace(key, binary_dict.get(key))
        self.text_body = self.text_body.decode('utf-8')
        self.headline = self.headline.decode('utf-8')
        for key in non_ascii_dict.keys():
            self.text_body = self.text_body.replace(key, non_ascii_dict.get(key))
            self.headline = self.headline.replace(key, non_ascii_dict.get(key))

