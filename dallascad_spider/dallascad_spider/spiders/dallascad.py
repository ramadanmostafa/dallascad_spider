# -*- coding: utf-8 -*-
import scrapy
from scrapy.http import FormRequest
from selenium import webdriver
import lxml.html
from ..items import DallascadSpiderItem
from scrapy.utils.markup import remove_tags

class DallascadSpider(scrapy.Spider):
    """
    scrapy crawl dallascad -o output_file.json -a file_path='input.txt'
    """
    name = "dallascad"
    allowed_domains = ["dallascad.org"]
    start_urls = (
        'http://www.dallascad.org/SearchOwner.aspx',
    )

    def __init__(self, file_path='', domain=None, *args, **kwargs):
        """
        Spider Constructor to read data from the input file and save them in self.owner_names list
        """
        super(DallascadSpider, self).__init__(*args, **kwargs)
        self.owner_names = []
        try:
            file_handle = open(file_path, 'r')
            for line in file_handle:
                self.owner_names.append(line.strip())
            file_handle.close()
        except IOError as e:
            print "No such file or directory: " + file_path

    def parse(self, response):
        """
        submit the search from with the owner names one by one
        """
        for owner_name in self.owner_names:
            yield FormRequest.from_response(response,
                                    formdata={'txtOwnerName': owner_name},
                                    clickdata={'name': 'cmdSubmit'},
                                    callback=self.parse_results,
                                    meta={"owner_name":owner_name})

    def parse_results(self, response):
        """
        yield a Request to get all the 10 results shown and uses selenium to click on the next link to get the next 10 results
        """
        result_urls_xpath = '//*[@id="Hyperlink1"]/@href'
        next_link_xpath = '//*[@id="SearchResults1_dgResults"]/tbody/tr[1]/td[1]/a[%d]'

        #get results urls
        result_urls = response.xpath(result_urls_xpath).extract()
        for url in result_urls:
            yield scrapy.Request(response.urljoin(url), self.parse_item)

        #get result_urls from the next pages
        driver = webdriver.Chrome()
        driver.get(response.url)
        driver.find_element_by_id('txtOwnerName').clear()
        driver.find_element_by_id('txtOwnerName').send_keys(response.meta["owner_name"])
        driver.find_element_by_id('cmdSubmit').click()
        i = 1
        while True:
            try:
                driver.find_element_by_xpath(next_link_xpath % i).click()
                i = 2
                #extract the next 10 results url and yield a Request to extract the data
                for url in lxml.html.fromstring(driver.page_source).xpath(result_urls_xpath):
                    yield scrapy.Request(response.urljoin(url), self.parse_item)
            except:
                #Exception happened which means this page has no Next link so we're done
                driver.close()
                return

    def parse_item(self, response):
        """
        parse the required tables then yield the item
        """
        item = DallascadSpiderItem()

        item['url'] = response.url

        #parse Property Location (Current 2017) table
        #xpath
        property_location_address_xpath = '//*[@id="PropAddr1_lblPropAddr"]/text()'
        property_location_Neighborhood_xpath = '//*[@id="lblNbhd"]/text()'
        property_location_Mapsco_xpath = '//*[@id="lblMapsco"]/text()'
        #extract
        item['property_location_address'] = response.xpath(property_location_address_xpath).extract_first()
        item['property_location_Neighborhood'] = response.xpath(property_location_Neighborhood_xpath).extract_first()
        item['property_location_Mapsco'] = response.xpath(property_location_Mapsco_xpath).extract_first()

        #parse Owner (Current 2017) table
        #xpath
        owner_xpath1 = '//*[@id="Form1"]/table/tbody/tr/td/div/text()'
        owner_xpath2 = '//*[@id="Form1"]/table/tr/td/div/text()'
        #extract
        item['owner'] = filter(lambda x: x!= '', map(unicode.strip, response.xpath(owner_xpath1).extract()))
        if len(item['owner']) == 0:
            item['owner'] = filter(lambda x: x!= '', map(unicode.strip, response.xpath(owner_xpath2).extract()))
        item['owner'] = ' '.join(item['owner'])

        #parse Multi-Owner (Current 2017) table
        #xpath
        tmp_data_xpath = '//*[@id="MultiOwner1_dgmultiOwner"]'
        Owner_Name_xpath = '//*[@id="MultiOwner1_dgmultiOwner"]/tr[2]/td[1]/text()'
        Ownership_percentage_xpath = '//*[@id="MultiOwner1_dgmultiOwner"]/tr[2]/td[2]/text()'
        #extract
        tmp_data = response.xpath(tmp_data_xpath).extract()
        if len(tmp_data) == 0:
            item['Owner_Name'] = ''
            item['Ownership_percentage'] = ''
        else:
            item['Owner_Name'] = response.xpath(Owner_Name_xpath).extract_first()
            item['Ownership_percentage'] = response.xpath(Ownership_percentage_xpath).extract_first()

        #parse Legal Desc (Current 2017) table
        #xpath
        legal_Desc_xpath = '//*[@id="Table8"]/tr/td/span/text()'
        #extract
        item['legal_Desc'] = ' \n'.join(response.xpath(legal_Desc_xpath).extract())

        #parse Value table
        #xpath
        value1_xpath = '//*[@id="BPPValue1_lblApprYr"]/text()'
        value2_xpath = '//*[@id="ValueSummary1_lblApprYr"]/text()'
        Improvement_xpath = '//*[@id="ValueSummary1_lblImpVal"]/text()'
        Land_xpath = '//*[@id="ValueSummary1_pnlValue_lblLandVal"]/text()'
        Market_Value_xpath = '//*[@id="ValueSummary1_pnlValue_lblTotalVal"]/text()'
        Capped_Value_xpath = '//*[@id="tblValueSum"]/tr[3]/td/span[2]/text()'
        Revaluation_Year_xpath = '//*[@id="ValueSummary1_lblRevalYr"]/text()'
        Previous_Revaluation_Year_xpath = '//*[@id="ValueSummary1_lblPrevRevalYr"]/text()'
        #extract
        item['value'] = response.xpath(value1_xpath).extract_first()
        if item['value'] == '':
            item['value'] = response.xpath(value2_xpath).extract_first()
        item['Improvement'] = response.xpath(Improvement_xpath).extract_first()
        item['Land'] = response.xpath(Land_xpath).extract_first()
        item['Market_Value'] = response.xpath(Market_Value_xpath).extract_first()
        item['Capped_Value'] = response.xpath(Capped_Value_xpath).extract_first()
        item['Revaluation_Year'] = response.xpath(Revaluation_Year_xpath).extract_first()
        item['Previous_Revaluation_Year'] = response.xpath(Previous_Revaluation_Year_xpath).extract_first()

        #get Residential_Account number
        #xpath
        Residential_Account_xpath = '//*[@id="lblPageTitle"]/text()'
        #extract
        item['Residential_Account'] = response.xpath(Residential_Account_xpath).extract_first()

        #parse Main Improvement (Current 2017) table
        #xpath
        main_improvement_table_xpath = '//*[@id="MainImpRes1_pnlMainImp"]'
        main_improvement_table_data_xpath = '//*[@id="MainImpRes1_pnlMainImp"]/table/tr/td/span/text()'
        #extract
        main_improvement_table = response.xpath(main_improvement_table_xpath).extract()
        main_improvement_table_data = response.xpath(main_improvement_table_data_xpath).extract()
        if len(main_improvement_table) > 0:
            try:
                #col1
                item['Building_Class'] = main_improvement_table_data[0]
                item['Year_Built'] = main_improvement_table_data[4]
                item['Effective_Year_Built'] = main_improvement_table_data[7]
                item['Actual_Age'] = main_improvement_table_data[10]
                item['Desirability'] = main_improvement_table_data[13]
                item['Living_Area'] = main_improvement_table_data[16]
                item['Total_Area'] = main_improvement_table_data[19]
                item['Complete'] = main_improvement_table_data[22]
                item['Stories'] = main_improvement_table_data[25]
                item['Depreciation'] = main_improvement_table_data[28]

                #col2
                item['Construction_Type'] = main_improvement_table_data[1]
                item['Foundation'] = main_improvement_table_data[5]
                item['Roof_Type'] = main_improvement_table_data[8]
                item['Roof_Material'] = main_improvement_table_data[11]
                item['Fence_Type'] = main_improvement_table_data[14]
                item['Ext_Wall_Material'] = main_improvement_table_data[17]
                item['Basement'] = main_improvement_table_data[20]
                item['Heating'] = main_improvement_table_data[23]
                item['Air_Condition'] = main_improvement_table_data[26]

                #col3
                item['Baths_Full_Half'] = main_improvement_table_data[2] + main_improvement_table_data[3]
                item['Kitchens'] = main_improvement_table_data[6]
                item['Bedrooms'] = main_improvement_table_data[9]
                item['Wet_Bars'] = main_improvement_table_data[12]
                item['Fireplaces'] = main_improvement_table_data[15]
                item['Sprinkler'] = main_improvement_table_data[18]
                item['Deck'] = main_improvement_table_data[21]
                item['Spa'] = main_improvement_table_data[24]
                item['Pool'] = main_improvement_table_data[27]
                item['Sauna'] = main_improvement_table_data[29]
            except:
                pass

        #parse Additional Improvements (Current 2017) table
        #xpath
        additional_improvement_table_xpath = '//*[@id="ResImp1_dgImp"]'
        additional_improvement_table_data_xpath = '//*[@id="ResImp1_dgImp"]/tr/td/text()'
        #extract
        additional_improvement_table = response.xpath(additional_improvement_table_xpath).extract()
        additional_improvement_table_data = response.xpath(additional_improvement_table_data_xpath).extract()
        item['Improvement_Type'] = ''
        item['Construction'] = ''
        item['Floor'] = ''
        item['Exterior_Wall'] = ''
        item['Area_sqft'] = ''
        if len(additional_improvement_table) > 0:
            for i in range(0, len(additional_improvement_table_data), 6):
                item['Improvement_Type'] += " " + additional_improvement_table_data[i+ 1].strip()
                item['Construction'] += " " + additional_improvement_table_data[i + 2].strip()
                item['Floor'] += " " + additional_improvement_table_data[i + 3].strip()
                item['Exterior_Wall'] += " " + additional_improvement_table_data[i + 4].strip()
                item['Area_sqft'] += " " + additional_improvement_table_data[i + 5].strip()

        #parse Land (2016 Certified Values) table
        #xpath
        land_table_xpath = '//*[@id="Land1_dgLand"]'
        land_table_data_xpath = '//*[@id="Land1_dgLand"]/tr/td/text()'
        Area_xpath = '//*[@id="Land1_dgLand__ctl2_Label1"]/text()'
        AdjustedPrice_xpath = '//*[@id="Land1_dgLand"]/tr[2]/td[10]/span/text()'
        #extract
        land_table = response.xpath(land_table_xpath).extract()
        land_table_data = filter(lambda x:x!='', map(unicode.strip, response.xpath(land_table_data_xpath).extract()))
        if len(land_table) > 0:
            item['StateCode'] = land_table_data[1]
            item['Zoning'] = land_table_data[2]
            item['Frontage'] = land_table_data[3]
            item['Depth'] = land_table_data[4]
            item['Area'] = response.xpath(Area_xpath).extract_first()
            item['Pricing_Method'] = land_table_data[5]
            item['UnitPrice'] = land_table_data[6]
            item['MarketAdjustment'] = land_table_data[7]
            item['AdjustedPrice'] = response.xpath(AdjustedPrice_xpath).extract_first()
            item['Ag_Land'] = land_table_data[8]

        #parse Exemptions (2016 Certified Values) table
        #xpath
        Exemptions_table_data_xpath = '//*[@id="Form1"]/table[2]/tbody/tr[2]/td/div[4]/table/tr/td/text()'
        Exemptions_table_xpath = '//*[@id="lblExempt"]/text()'
        #extract
        Exemptions_table_data = response.xpath(Exemptions_table_data_xpath).extract()
        Exemptions_table = response.xpath(Exemptions_table_xpath).extract_first()
        if Exemptions_table is not None and "Exemptions" in Exemptions_table:
            try:
                item['City_Taxing_Jurisdiction'] = Exemptions_table_data[0]
                item['School_Taxing_Jurisdiction'] = Exemptions_table_data[1]
                item['County_and_School_Equalization_Taxing_Jurisdiction'] = Exemptions_table_data[2]
                item['College_Taxing_Jurisdiction'] = Exemptions_table_data[3]
                item['Hospital_Taxing_Jurisdiction'] = Exemptions_table_data[4]
                item['Special_District_Taxing_Jurisdiction'] = Exemptions_table_data[5]
                item['City_HOMESTEAD_EXEMPTION'] = Exemptions_table_data[6]
                item['School_HOMESTEAD_EXEMPTION'] = Exemptions_table_data[7]
                item['County_and_School_Equalization_HOMESTEAD_EXEMPTION'] = Exemptions_table_data[8]
                item['College_HOMESTEAD_EXEMPTION'] = Exemptions_table_data[9]
                item['Hospital_HOMESTEAD_EXEMPTION'] = Exemptions_table_data[10]
                item['Special_District_HOMESTEAD_EXEMPTION'] = Exemptions_table_data[11]
                item['City_OTHER_EXEMPTION'] = Exemptions_table_data[12]
                item['School_OTHER_EXEMPTION'] = Exemptions_table_data[13]
                item['County_and_School_Equalization_OTHER_EXEMPTION'] = Exemptions_table_data[14]
                item['College_OTHER_EXEMPTION'] = Exemptions_table_data[15]
                item['Hospital_OTHER_EXEMPTION'] = Exemptions_table_data[16]
                item['Special_District_OTHER_EXEMPTION'] = Exemptions_table_data[17]
            except Exception as e:
                pass

        yield item
