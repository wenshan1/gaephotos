from uliweb.core.dispatch import bind
import uliweb

@bind('startup')
def startup(sender):
    from uliweb import orm
    
    orm.set_debug_query(uliweb.settings.ORM.DEBUG_LOG)
    orm.set_auto_create(uliweb.settings.ORM.AUTO_CREATE)
    orm.get_connection(uliweb.settings.ORM.CONNECTION)

    if 'MODELS' in uliweb.settings:
        for k, v in uliweb.settings.MODELS.items():
            orm.set_model(v, k)