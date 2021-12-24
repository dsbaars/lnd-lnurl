import urllib
import lnurl
from lnurl import LnurlResponse
import requests
from grpc_gen.lightning_pb2 import _PAYMENT_PAYMENTSTATUS
from lnd import Lnd
from urllib.parse import urlsplit, parse_qsl, urlunsplit, urlencode

class LndLnurl:
    def __init__(self, config, arguments):
        self.config = config
        self.lnurl = arguments.LNURL
        self.isLightningAddress = False
        if "@" in self.lnurl:
            self.isLightningAddress = True
        else: 
            try:
                self.decoded = lnurl.decode(self.lnurl)
            except lnurl.exceptions.InvalidLnurl:
                raise ValueError("Invalid LNURL")
        self.session = None
        self.lnd = Lnd(
            config.get('lnd', 'rpcserver'),
            config.get('lnd', 'tlscertpath'),
            config.get('lnd', 'macaroonpath')
        )
        nodeinfo = self.lnd.getNodeInfo()
        print ("Connected with node %s (LND %s)" % (nodeinfo.alias, nodeinfo.version))
        print ("--------------------------------------------------------------------------------")
        return

    def get_session(self):
        if (self.session):
            return self.session
        self.session = requests.session()
        if (self.config.getboolean('tor', 'active')):
            self.session.proxies = {'http':  'socks5://%s' % self.config.get('tor', 'socks'),
                                    'https': 'socks5://%s' % self.config.get('tor', 'socks')}
        return self.session

    def run(self):
        session = self.get_session()

        if self.isLightningAddress:
            [handle, domain] = self.lnurl.split('@')
            try:
                self.r = session.get('https://%s/.well-known/lnurlp/%s' % (domain, handle))
                self.res = self.r.json()
            except requests.exceptions.HTTPError as err:
                print("The domain %s does not support lightning address." % domain)
                return
            except:
                print("Error processing lightning address.")
                return
        else:
            self.r  = session.get(str(self.decoded))
            self.res = self.r.json()
        func =  {
            "payRequest": self.payRequest,
            "withdrawRequest": self.withdrawRequest,
            "channelRequest": self.channelRequest,
            "hostedChannelRequest": self.hostedChannelRequest
        }
        if not 'tag' in self.res:
            print("Unexpected response, is your lightning-address or LNURL correct?")
            return
        func[self.res['tag']]()
        return

    def payRequest(self):
        session = self.get_session()
        res = LnurlResponse.from_dict(self.r.json())
        print("Metadata: %s" % res.metadata.text)
        print("Pay Request - Min %s / Max %s satoshi" % (res.min_sats, res.max_sats))
        amount = None
        while amount is None or int(amount) < res.min_sats or int(amount) > res.max_sats: 
            amount = input("How much do you want to pay (in sats): ")
        callback = res.callback + "?amount=" + str(int(amount) * 1000)
        self.r  = session.get(callback)
        res = self.r.json()
        print("LN invoice: %s" % res['pr'])
        print("---------------------------")
        print("Attempting payment")
        payResponse = self.lnd.payInvoice(res['pr'])
        for r in payResponse:
            print("Status: %s" % _PAYMENT_PAYMENTSTATUS.values[r.status].name)
            if r.status == 2:
                print("%s hops, total amount %s msat" % (len(r.htlcs[0].route.hops), r.htlcs[0].route.total_amt_msat))
        return

    def withdrawRequest(self):
        session = self.get_session()

        print("Metadata: %s" % self.res['defaultDescription'])
        print("Withdraw Request - Min %s / Max %s satoshi" % (self.res['minWithdrawable'] / 1000, self.res['maxWithdrawable'] / 1000))
        print("NOTE: Always withdraw the max amount at Stekking or you will lose sats")
        amount = None
        while amount is None or int(amount) < self.res['minWithdrawable'] / 1000 or int(amount) > self.res['maxWithdrawable'] / 1000: 
            amount = input("How much do you want to withdraw (in sats) or leave empty for %s sats: " % str(self.res['maxWithdrawable'] / 1000))
            if amount == "":
                amount = self.res['maxWithdrawable'] / 1000
        print("Creating an invoice for %s sats" % amount)

        lnInvoice = self.lnd.createInvoice(amount, self.res['defaultDescription'])

        [scheme, netloc, path, query, fragment] = urlsplit(self.res['callback'])
        query_params = parse_qsl(query)

        if (self.res['k1']):
            query_params.append(('k1', self.res['k1']))
        query_params.append(('pr', lnInvoice.payment_request))
        new_query_string = urlencode(query_params, doseq=True)

        callback = urlunsplit((scheme, netloc, path, new_query_string, fragment))

        self.r  = session.get(callback)
        res = LnurlResponse.from_dict(self.r.json())
        print("---------------------------")
        print (res.status)
        if (res.status == "ERROR"):
            print(res.reason)
        return

    def channelRequest(self):
        print("Not implemented")
        return

    def hostedChannelRequest(self):
        print("Not implemented")
        return

