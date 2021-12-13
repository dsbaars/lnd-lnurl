import lnurl
from lnurl import LnurlResponse
import requests
from lnd import Lnd

class LndLnurl:
    def __init__(self, config, arguments):
        self.config = config
        self.lnurl = arguments.LNURL
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
        self.r  = session.get(str(self.decoded))
        self.res = self.r.json()
        func =  {
            "payRequest": self.payRequest,
            "withdrawRequest": self.withdrawRequest,
            "channelRequest": self.channelRequest,
            "hostedChannelRequest": self.hostedChannelRequest
        }

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
        res = LnurlResponse.from_dict(self.r.json())
        print("LN invoice: %s" % res.pr)
        print("---------------------------")
        payResponse = self.lnd.payInvoice(res.pr)
        for r in payResponse:
            print(r)
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

        callback = self.res['callback'] + "&pr=" + lnInvoice.payment_request
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

