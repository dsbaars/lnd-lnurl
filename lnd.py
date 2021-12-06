import codecs
import os, random
from functools import lru_cache
from os.path import expanduser

import grpc

from grpc_gen import router_pb2 as lnrouter
from grpc_gen import router_pb2_grpc as lnrouterrpc
from grpc_gen import lightning_pb2 as ln
from grpc_gen import lightning_pb2_grpc as lnrpc
from grpc_gen import invoices_pb2 as lninvoices
from grpc_gen import invoices_pb2_grpc as lninvoicesrpc

MESSAGE_SIZE_MB = 50 * 1024 * 1024

class Lnd:
    def __init__(self, server, cert, macaroon):
        os.environ["GRPC_SSL_CIPHER_SUITES"] = "HIGH+ECDSA"
        combined_credentials = self.get_credentials(cert, macaroon)
        channel_options = [
            ("grpc.max_message_length", MESSAGE_SIZE_MB),
            ("grpc.max_receive_message_length", MESSAGE_SIZE_MB),
        ]
        grpc_channel = grpc.secure_channel(
            server, combined_credentials, channel_options
        )
        self.stub = lnrpc.LightningStub(grpc_channel)
        self.router_stub = lnrouterrpc.RouterStub(grpc_channel)
        self.invoices_stub = lninvoicesrpc.InvoicesStub(grpc_channel)

    @staticmethod
    def get_credentials(cert, macaroon):
        tls_certificate = open(os.path.expanduser(cert), 'rb').read()
        ssl_credentials = grpc.ssl_channel_credentials(tls_certificate)
        with open(macaroon, "rb") as f:
            macaroon = codecs.encode(f.read(), "hex")
        auth_credentials = grpc.metadata_call_credentials(
            lambda _, callback: callback([("macaroon", macaroon)], None)
        )
        combined_credentials = grpc.composite_channel_credentials(
            ssl_credentials, auth_credentials
        )
        return combined_credentials

    def createInvoice(self, value, memo):
        request = ln.Invoice(
            memo=memo,
            value=int(value),
            expiry=3600,            
        )

        response = self.stub.AddInvoice(request)
        return response
    
    def payInvoice(self, pr):
        request = lnrouter.SendPaymentRequest(
            payment_request=pr,
            no_inflight_updates=False,
            timeout_seconds=2
        )
        response = self.router_stub.SendPaymentV2(request)
        return response
    
    def getNodeInfo(self):
        request = ln.GetInfoRequest()
        return self.stub.GetInfo(request)