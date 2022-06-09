from tested import app,sio
import ssl
import logging

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.basicConfig(level=logging.INFO)
    logging.basicConfig(level=logging.WARNING)
    logging.basicConfig(level=logging.ERROR)
    logging.basicConfig(level=logging.CRITICAL)
   
    app.threaded='true' 
    #
    sio.run(app,host="0.0.0.0",port=8080,debug=True,use_reloader=True)