from uliweb.middleware import Middleware

class TransactionMiddle(Middleware):
    ORDER = 100
    
    def __init__(self, application, settings):
        from uliweb.orm import get_connection
        self.db = get_connection()
        
    def process_request(self, request):
        self.db.begin()

    def process_response(self, request, response):
        self.db.commit()
        return response
            
    def process_exception(self, request, exception):
        self.db.rollback()
    