import cPickle
from base import BaseStorage, StorageError

try:
    import sqlalchemy as sa
    from sqlalchemy import types
except ImportError:
    raise StorageError("Database cache backend requires the 'sqlalchemy' library")

class Storage(BaseStorage):
    def __init__(self, options):
        self.url = options.get('url', 'sqlite:///')
        self.tablename = options['table_name']
        self.auto_create = options.get('auto_create', True)
        self.db, self.meta, self.table = create_table(self.url, self.tablename, self.auto_create)
        
    def get_lock(self, key):
        return True
    
    def read_ready(self, key):
        return True
        
    def acquire_read_lock(self, lock):
        return self.db.begin()
        
    def release_read_lock(self, lock, success):
        if success:
            return self.db.commit()
        else:
            return self.db.rollback()
        
    def acquire_write_lock(self, lock):
        return self.db.begin()
        
    def release_write_lock(self, lock, success):
        if success:
            return self.db.commit()
        else:
            return self.db.rollback()
      
    def load(self, key):
        if key:
            result = sa.select([self.table.c.data, self.table.c.expiry_time,
                                self.table.c.stored_time], 
                               self.table.c.key==key,
                              for_update=True).execute().fetchone()
            if result:
                try:
                    v = cPickle.loads(result['data'])
                    return result['stored_time'], result['expiry_time'], v
                except (IOError, OSError, EOFError, cPickle.PickleError, ValueError):
                    pass
                
    
    def save(self, key, stored_time, expiry_time, value, modified):
        if key:
            v = cPickle.dumps(value)
            result = sa.select([self.table.c.data, self.table.c.id], 
                               self.table.c.key==key,
                              for_update=True).execute().fetchone()
            if result:
                self.table.update(self.table.c.id==result['id']).execute(
                    data=v, stored_time=stored_time, expiry_time=expiry_time)
            else:
                self.table.insert().execute(key=key, data=v,
                                   stored_time=stored_time, expiry_time=expiry_time)
    
    def delete(self, key):
        if key:
            self.table.delete(self.table.c.key==key).execute()
            
    def delete_lock(self, lock):
        pass
    
def create_table(url, tablename, create=False):
    db = sa.create_engine(url, strategy='threadlocal')
    meta = sa.MetaData(db)
    table = sa.Table(tablename, meta,
                     sa.Column('id', types.Integer, primary_key=True),
                     sa.Column('key', types.String(64), nullable=False),
                     sa.Column('stored_time', types.Integer, nullable=False),
                     sa.Column('expiry_time', types.Integer, nullable=False),
                     sa.Column('data', types.PickleType, nullable=False),
                     sa.UniqueConstraint('key')
    )
    if create:
        table.create(checkfirst=True)
    return db, meta, table
    