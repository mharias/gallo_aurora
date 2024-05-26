import datetime
import time
import urllib
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
from datetime import datetime,timedelta
import calendar
from pytz import timezone
import googlemaps
import pandas as pd
import sys
import tweepy

#sys.path.append("/Users/mharias/documents/proyectos/mylibs") # directorio de acceso a librerías auxiliares
sys.path.append("/home/waly00/claves") # directorio de acceso a librerías auxiliares

from pass_elgallo import token_elgalloaurora,apikey,apisecretkey,AccessToken,AccessTokenSecret,google_key

from astral import LocationInfo
from astral.sun import sun
import sched


class Gallo:

    
    def __init__(self,google_key_,path_proyecto,token_elgalloaurora,apikey,apisecretkey,AccessToken,AccessTokenSecret):
       self.google_key=google_key_
       self.path_proyecto = path_proyecto
       self.token = token_elgalloaurora
       self.apikey = apikey
       self.apisecretkey = apisecretkey
       self.AccessToken = AccessToken
       self.AccessTokenSecret = AccessTokenSecret
       return
        
    def load_cities_formatted(self,fichero_ciudades_formateados):
        cities=pd.read_csv(fichero_ciudades_formateados).set_index('Ciudad')
        self.ciudades=cities
        return cities
    
    def load_cities_raw(self,fichero_ciudades_raw):
        def loc(x):
            print (f"Geocode {x}")
            return gmaps.geocode(x)[0]['geometry']['location']

        def tz(x):
            print (f"Tzone {x}")
            return gmaps.timezone(x)
        gmaps = googlemaps.Client(key=google_key)
        ciudades = (pd.read_csv(fichero_ciudades_raw,names=['Pais','Ciudad','Continente']).loc[:,:]
        .assign(localizacion = lambda x : x['Ciudad']+','+x['Pais'])
        .assign(localizacion = lambda df_ : df_.localizacion.map(loc))
        .assign(longitud= lambda df_ : df_.localizacion.map(lambda x : dict(x)['lng']))
        .assign(latitud= lambda df_ : df_.localizacion.map(lambda x : dict(x)['lat']))
        .assign(timezone = lambda df_ : df_.localizacion.map(tz))
        .assign(dstOffset = lambda df_ : df_.timezone.map(lambda x: dict(x)['dstOffset']))
        .assign(rawOffset = lambda df_ : df_.timezone.map(lambda x: dict(x)['rawOffset']))
        .assign(timeZoneId = lambda df_ : df_.timezone.map(lambda x: dict(x)['timeZoneId']))
        .assign(timeZoneName = lambda df_ : df_.timezone.map(lambda x: dict(x)['timeZoneName']))
        .loc[:,['Ciudad','Pais','Continente','longitud','latitud','dstOffset','rawOffset','timeZoneId','timeZoneName']]
        .set_index()
                        )
        self.ciudades=ciudades
        return ciudades
        
    def save_cities(self,path_fichero):
        self.ciudades.to_csv(path_fichero,header=False,index=False)

        
    
    
    def mapa(self,ciudad,path):
        plt.figure(figsize=(12,6))
        map = Basemap(llcrnrlon=-160, llcrnrlat=-75,urcrnrlon=160,urcrnrlat=80,lon_0=100)
        #map = Basemap(llcrnrlon=-16, llcrnrlat=-75,urcrnrlon=160,urcrnrlat=80)
        # plot coastlines, draw label meridians and parallels.
        map.drawcoastlines()
        map.drawparallels(np.arange(-90,90,30),labels=[1,0,0,0])
        map.drawmeridians(np.arange(map.lonmin,map.lonmax+30,60),labels=[0,0,0,1])
        # fill continents 'coral' (with zorder=0), color wet areas 'aqua'
        map.drawmapboundary(fill_color='aqua')
        #map.drawmapboundary(fill_color='#A6CAE0', linewidth=0)
        #map.fillcontinents(color='coral',lake_color='aqua')
        map.fillcontinents(color='coral', alpha=0.7, lake_color='grey')
        map.drawcoastlines(linewidth=0.1, color="white")

        date = datetime.now(timezone('utc'))
        CS=map.nightshade(date)
        
        # Add a marker per city of the data frame!
        map.plot(self.ciudades.loc[ciudad,'longitud'], self.ciudades.loc[ciudad,'latitud'], linestyle='none', marker='o', markersize=16, 
                 alpha=0.6, c="blue", markeredgecolor="black", markeredgewidth=1)
        plt.title('Day/Night Map for {} (UTC)'.format(date.strftime("%d %b %Y %H:%M:%S")))
        path_fichero = f"{self.path_proyecto}img/mapa.png"
        plt.savefig(path_fichero)
        plt.show()
        plt.close() #añadido para evitar muchas abiertas
        return path_fichero
    
   
    def enviar_tweet(self,accion,ciudad,hora_utc,nueva_hora,path_fichero):
        CR='\n'
        hora='%H:%M:%S'
        textos={'amanece':('Good morning','sun rising'),'anochece':('Good evening','sunset')}
        auth = tweepy.OAuth1UserHandler(self.apikey,self.apisecretkey)
        auth.set_access_token(self.AccessToken,self.AccessTokenSecret)
        api = tweepy.API(auth)
        media = api.media_upload(filename=path_fichero)
        media_id = media.media_id
        cliente = tweepy.Client(bearer_token=self.token,
                          consumer_key=self.apikey,
                          consumer_secret=self.apisecretkey,
                          access_token=self.AccessToken,
                          access_token_secret=self.AccessTokenSecret)
        Text1=('{}, {} at {}, {} ({})'.format(textos[accion][0],textos[accion][1],'#'+ciudad.replace(' ',''),
                                                                  '#'+self.ciudades.loc[ciudad,'Pais'],
                                                                  '#'+self.ciudades.loc[ciudad,'Continente']))
        Text2=('{0:<10} {1:<15}'.format('UTC time',hora_utc.strftime(hora)))
        Text3=('{0:<10} {1:<15}'.format('Local time',hora_utc.astimezone(timezone(self.ciudades.loc[ciudad,'timeZoneId'])).strftime(hora)))
        Text4=('{0:<10} {1} at {2:<15}'.format('Tomorrow',textos[accion][1],nueva_hora.strftime(hora)))
        #Text5='#roostercrow'
        Text5='#elgallodelaaurora'
        texto=Text1+CR+Text2+CR+Text3+CR+Text4+CR+Text5
        print (texto)
        #return cliente.create_tweet(text=texto)
        return cliente.create_tweet(text=texto,media_ids=[media_id])

    
    def run(self):
        self.s.run()
        return
    
    
    def inicia_schedule(self):
        for i in self.ciudades.index:
            city = LocationInfo(i, self.ciudades.loc[i,'Pais'], self.ciudades.loc[i,'timeZoneId'], self.ciudades.loc[i,'latitud'], self.ciudades.loc[i,'longitud'])
            hoy = datetime.today() #.astimezone(timezone(ciudades.loc[i,'timeZoneId']))
            
            sol = sun(city.observer, date=hoy)
            print (f"{city.name}: amanece a las {sol['sunrise'].strftime('%H:%M')}/{sol['sunrise'].astimezone(timezone(self.ciudades.loc[i,'timeZoneId'])).strftime('%H:%M')}@{calendar.timegm(sol['sunrise'].timetuple())}, anochece a las {sol['sunset'].strftime('%H:%M')}@{calendar.timegm(sol['sunset'].timetuple())}")
            if sol['sunrise']>datetime.now(timezone('UTC')):
                self.s.enterabs(calendar.timegm(sol['sunrise'].timetuple()),1,self.accion,kwargs={'ciudad':city.name,'que':'amanece','hora':sol['sunrise']})
                print(f"Añadida nueva hora amanecer: {sol['sunrise'].astimezone(timezone(self.ciudades.loc[city.name,'timeZoneId'])).strftime('%H:%M')}")
            else:
                sol = sun(city.observer, date=hoy+timedelta(days=1))
                self.s.enterabs(calendar.timegm(sol['sunrise'].timetuple()),1,self.accion,kwargs={'ciudad':city.name,'que':'amanece','hora':sol['sunrise']})
                print(f"Añadida nueva hora amanecer:{sol['sunrise'].astimezone(timezone(self.ciudades.loc[city.name,'timeZoneId'])).strftime('%H:%M')}")
            if sol['sunset']>datetime.now(timezone('UTC')):
                self.s.enterabs(calendar.timegm(sol['sunset'].timetuple()),1,self.accion,kwargs={'ciudad':city.name,'que':'anochece','hora':sol['sunset']})
                print(f"Añadida nueva hora anochecer: {sol['sunset'].astimezone(timezone(self.ciudades.loc[city.name,'timeZoneId'])).strftime('%H:%M')}")
            else:
                sol = sun(city.observer, date=hoy+timedelta(days=1))
                self.s.enterabs(calendar.timegm(sol['sunset'].timetuple()),1,self.accion,kwargs={'ciudad':city.name,'que':'anochece','hora':sol['sunset']})
                print(f"Añadida nueva hora anochecer: {sol['sunset'].astimezone(timezone(self.ciudades.loc[city.name,'timeZoneId'])).strftime('%H:%M')}")
        
            
               
        return


if __name__ == "__main__":
    fichero='cities.csv'
    fichero_formateado_corto='cities_formatted.csv'
    fichero_formateado_largo = 'cities_long_formatted.csv'
    #path_proyecto = '/Users/mharias/documents/proyectos/gallo_aurora/'
    path_proyecto = '/home/waly00/gallo_aurora/'
    gallo=Gallo(google_key,path_proyecto,token_elgalloaurora, apikey, apisecretkey, AccessToken,AccessTokenSecret)
    gallo.ciudades = gallo.load_cities_formatted(fichero_formateado_corto)
    gallo.s = sched.scheduler(time.time,time.sleep)
    gallo.inicia_schedule()
    gallo.run()