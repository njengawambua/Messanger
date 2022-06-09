
from flask import Flask, render_template,request,session,g,current_app,redirect,url_for,make_response
from flask_socketio import SocketIO,join_room,leave_room,rooms
from datetime import  datetime
import json
import sqlite3
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from random import random
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
maindb='maindb.sqlite3'
import os
from threading import Thread
import requests
from requests import Request
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
sio = SocketIO(app,async_mode="threading")
mainn=0


def getdb(maindb):
  try:
    db = sqlite3.connect(maindb)
    return db
  except:
    return "db conn failed"


@app.route('/signout')
def signout():
  if 'User' in session.keys():
    session.pop('User')

    return render_template("login.html",nloc='home')

def getUser():
  try:
    print("getting db in get user")
    db=getdb(maindb)
    cur=db.cursor()
    print("got db")
    try:
      print("getting user")
      u=cur.execute("select * from Account").fetchone()
      if not u:
        print("no user in account")
        return False
      else:
        print("got user")
        us={'Id':u[0],'Name':u[1],'Email':u[2],'DP':u[3],'Role':u[4]}
        session['User']=us
        return us
    except:
      print("failed to get user")
      return False
  except:
    print("failed to get db")
    return False

@app.route('/')
def home():
  print("in home")
  s=getUser()
  print(s)
  if getUser():
    print("got session")
  else:
    print("session creation error")

  return render_template("msg.html")

def addfile(da,msid,userid):
  print("threading ")
  try:
    db=getdb(maindb)
    cur=db.cursor()
    print("got db")
    data=da['File']
    print("file number",len(data))
    for i in data:
      print(i)
      print(i['Ext'])
      n=str(int(random()*100000)) +"."+i['Ext']
      print(n)
      h="./static/Images/DP/"+n
      vs="./static/Images/"+n
      print(vs)
      fi=open(vs,"wb+")
      print(fi)
      print("write data")
      fi.write(i['File'])
      fi.flush()
      fi.close()
      print(n,msid,i['Type'])
      cur.execute("insert into MessageAtt (Name,MessageId,Type) values(?,?,?)",([n,msid,i['Type']]))
      db.commit()
      print("added successfuly")
      i['File']=n
      dd=da
      i.pop('Name')
      dd['File']=i
      print(dd['File'])
      print(dd)
      dd['MsgId']=msid
      print("checking in where")
      if 'GroupId' in dd:
        data={
        "Name":dd['File']['File'],
        "MsgId":msid,
        "ChatId":dd['GroupId'],
        "Type":dd['File']['Type']
      }
        print("got group")
        sio.emit('recvatt',data,namespace="/group",callback=ack)
        pass
      if 'Chatid' in dd:
        data={
        "Name":dd['File']['File'],
        "MsgId":msid,
        "ChatId":dd['Chatid'],
        "Type":dd['File']['Type']
        }
        print("is not group")
        print(data)
        sio.emit('recvatt',data,namespace="/chat",callback=ack)
      print("emitted")
    print("inserting")
    sio.emit('ack',"recieved")
    da['Userid']=userid
    db.close()
    print("threading ")
    return
  except:
    db.rollback()
    db.close()
    return "failed to save files"

@app.route('/ch/<Id>')
def ch(Id):
  return render_template("chat.html",Id=Id)

@sio.on("joinchat",namespace="/chat")
def join(chatid):
  print("in joinchat")
  print(session.keys())
  user=session['User']
  userid=user["Id"]
  print("\n got data",chatid)
  print("\n userid",userid)
  try:
    db=getdb(maindb)
    cur=db.cursor()
    print("got db")
    ###given chat id get
    rom=cur.execute("select * from Chats Where Id=?",([chatid])).fetchone()
    ctt=cur.execute("select * from Roommates where ChatId=? and MateId =?",([chatid,userid])).fetchone()
    ct=cur.execute("select * from Roommates where ChatId=? and MateId !=?",([chatid,userid])).fetchone()
    print("got query")
    if not ct and rom and ctt:
      print("not in this chat")
      return "not in this chat"
    else:
      print("in this chat",ct)
      sid=request.sid
      c=str(chatid)
      join_room(c,sid=sid,namespace="/chat")
      print("joined",chatid)
      try:
        print(rom[4])
        print(ct[1])
        m=cur.execute("select * from Account where Id=?",([ct[1]])).fetchone()
        if not m:
          print("no roommate data found")
          return
        print(m)
        data={'Name':m[1],'Dp':m[3],'Id':m[0]}
        ##emit this
        sio.emit("mydata",data,room=request.sid,namespace="/chat")
        print("\n user data",data)
        print("\n getting messages for chat",chatid)
        msgs=cur.execute("select * from Message where ChatId=?",([chatid])).fetchall()
        print("\n\n got messages for chat",chatid)
        if not msgs:
          print("no messages")
          return ("no messages")
        print("\n\n messages for chat",chatid,len(msgs))
        for msg in msgs:
          ###return dictionary obj
          print("looping msgs")
          print("\n msg",msg)
          mmsg={
                "Id":msg[0],
                "Msg":msg[3],
                "SentDate":msg[5],
                "ReatAt":msg[7],
                "UserId":msg[1],
                "Delivered":msg[6],
                "Status":msg[4],
                "MyId":userid,
                "ChatId":chatid
                }
          print("message object")
          print(mmsg)
          sio.emit("recvmsg",mmsg,room=request.sid,namespace="/chat")
          try:
            print("getting attatchment for message id",msg[0])
            msgatt=cur.execute("select * from MessageAtt where MessageId=?",([msg[0]])).fetchall()
            print("fetched attatchment")
            if not msgatt:
              print("no attatchment")
            else:
              print("atttchment list for message",msgatt)
              mfiles=[]
              for i in msgatt:
                #create dictionary
                print("getting attatchment",i[0])
                mat={}
                mat['Id']=i[0]
                mat['Name']=i[1]
                mat["Type"]=i[3]
                mat["MsgId"]=msg[0]
                mat["ChatId"]=chatid
                print("message object")
                print(mat)
                sio.emit("recvatt",mat,room=request.sid,namespace="/chat")
              ##emit here
          except :
            print("error in getting messages attatchments")
        print("message loop ended")
        cur.close()
        db.close()
        return
      except :
          cur.close()
          db.close()
          print("failed to get messages ")
          return("failed to get messages a")
  except:
    print("db failed")
    db.close()
    return "db failed"

def  getchatMessagesData(chatid):
  mymsg={}
  attl=[]
  try:
    print("getting db")
    db=sqlite3.connect(maindb)
    cur=db.cursor()
    print("got db and cursor")
    try:
      m=cur.execute("select * from Roommates where ChatId=? and MateId=?",([])).fetchone()
      if not m:
        print("not allowed in this room")
        return
      print(m)
      mdata=cur.execute("select * from Users where Id=?",([])).fetchone()
      if not mdata:
        print("no chatmate records")
        return
      usn=mdata[1]+' '+mdata[2]+' '+mdata[3]
      data={'Name':usn,'Dp':mdata[8],'Id':mdata[0]}
      ##emit this
      print("\n getting messages for chat",chatid)
      msgs=cur.execute("select * from Message where ChatId=?",([chatid])).fetchall()
      print("\n\n got messages for chat",chatid)
      if not msgs:
        print("no messages")
        return ("no messages")
      print("\n\n messages for chat",msgs)
      for msg in msgs:
        ###return dictionary obj
        print("creating msg dict obj")
        mymsg["Id"]=msg[0]
        mymsg["msg"]=msg[3]
        print("\n message",msg[3])
        mymsg["sentDate"]=msg[5]
        mymsg["DeliveredDate"]=msg[6]
        mymsg["Status"]=msg[4]
        mymsg["ReadAt"]=msg[7]
        mymsg['UserId']=msg[1]
        try:
          print("getting attatchments")
          print("getting attatchment for message id",msg[0])
          msgatt=cur.execute("select * from MessageAtt where MessageId=?",([msg[0]])).fetchall()
          print("got attatchment")
          if not msgatt:
            print("no attatchment")
          else:
            print("atttchment list for message",msgatt)
            for i in msgatt:
              mat={}
              mat['Id']=i[0]
              mat['Name']=i[1]
              mat["Size"]=i[3]
              print("getting attatchment attributes for message id",msg[0])
            print("\n\n my messages",mymsg)
            ##emit here
        except :
          print("failed to get messages attatchments")
          return("failed to get messages attatchments")
      return mymsg
    except :
        cur.close()
        db.close()
        print("failed to get messages ")
        return("failed to get messages a")
  except :
        print("failed to get db ")
        return("failed to get db")
@sio.on("selectuser",namespace="/minehome")
def selectuser(data):
  ###check if in session
  ###if can create groups admin only
  #
  user=None
  if 'User' in session.keys():
    user=session['User']
  else:
    print("not in session.....\n sending to login page")
    return
  try:
    print("getting db")
    db=getdb(maindb)
    cur=db.cursor()
    print("got db")
    try:
      if user['Role']!='Admin':
        print("not allowed")
        return
      else:
        print("getting accountid list")
        uss=cur.execute("select AccountId from Chats where Type=?",(['Personal'])).fetchall()
        if not uss:
          print("did not get any body")
          return
        else:
          print("got accountid list")
          print(len(uss))
          print("looping thru list")
          for id in uss:
            print("getting account data for  ",id)
            da=cur.execute("select * from Account where Id=?",([id])).fetchall()
            if not da:
              print("did not get account data for  ",id)
            else:
              print("got get account data for  ",id)
              data={'Name':da[1],'Id':da[0],'DP':da[3],'Role':da[4]}
              sio.emit("userselect",data,room=request.sid,namespace="/minehome")

          print("loop ended......\n cloing db")
          cur.close()
          db.close()
          return
    except:
      print("failed to fetch user data")
      cur.close()
      db.close()
      return("failed to fetch user data")
  except:
    print("failed to get db")
    return("failed to get db")

td=Thread()
@sio.on("msg",namespace="/chat" )
def hanack(da):
 # c=request.sid
  print(da)
  print(rooms())
  for i in rooms():
    print(i,type(i))
  #print(c)
  date=datetime.now()
  dd={}
  user=session['User']
  userid=user['Id']
  ss=type(date)
  print(ss)
  rm=str(da['Chatid'])
  try:
    print("getting db")
    db=getdb(maindb)
    cur=db.cursor()
    chatid=da['Chatid']
    cc=cur.execute("select * from Roommates where ChatId=? and MateId=? and Status=?",([chatid,userid,"Active"])).fetchone()
    print(cc)
    if cc:
      chatid=da['Chatid']
      mssg=da['Msg']
      date=datetime.ctime(datetime.now())
      print("inserting")
      print(userid,chatid,mssg,type(date))
      msid=int(random()*10000000000)
      cur.execute("insert into Message (Id,UserId,ChatId,Message,Status,SentDate) values(?,?,?,?,?,?)",(msid,userid,chatid,mssg,'Active',date))
      db.commit()
      db.close()
      da['SentDate']=date
      da['Userid']=userid
      da['Id']=msid
      da["MyId"]=userid
      print("message saved")
      if 'File' in da:
        print("got file")
        print("got file")
        sio.emit('recvmsg',da,room=rm,namespace="/chat")
        td.run(addfile(da,msid,userid))
      else:
        print("no file")
        print(da)
        sio.emit('recvmsg',da,room=rm,namespace="/chat")
        print("got no file")
  except:
    print("db error")
    db.close()
    return "db error"


@app.route("/mediafile/<id>/<type>/<name>")
def mediafile(id,type,name):
  print(id)
  print(type)
  l={"Id":id,"Type":type,'Name':name}
  return render_template("postmedia.html",data=l)


@sio.on("managemsg",namespace='/chat')
def manageMsg(data):
    user=''
    if 'User' in session.keys():
        user=session['User']
    else:
        print("not in session")
        return
    print("got data \n\n",data)
    try:
        db=getdb(maindb)
        cur=db.cursor()
        print("got db")
        print(data['Id'],data['ChatId'])
        try:
            msg=cur.execute("select * from Message where Id=? and ChatId=?",([data['Id'],data['ChatId']])).fetchone()
           # usr=cur.execute("select * from Roommates where MateId=? and ChatId=?",([user[0],data['Chatid']])).fetchone()
            print("getting msg")
            if not msg:# and not usr:
                print("unable to get msg")
                return
            else:
                print("got msg \n",msg)
                date=datetime.now()
                date=datetime.ctime(date)
                if data['Type']=='Delete':
                    print("got delete")
                    print([user['Id'],data['Id'],date])
                    cur.execute("insert into DeletedBy(UserId,MsgId,Date) values (?,?,?)",([user['Id'],data['Id'],date]))
                    #sio.emit('managemsg',data,namespace="/chat")
                    db.commit()
                    db.close()
                    print("done deleting")
                    return
                if data['Type']=='Forward':
                    print("got forward message")
                    db.close()
                    return
                if data['Type']=='Reply':
                    print("got reply")
                    db.close()
                    return
        except:
            print("failed to get msg")
            db.rollback()
            db.close()
            return
    except:
        print("failed to get db")
        return


@sio.on("managemsg",namespace='/group')
def manageMsg(data):
    user=''
    if 'User' in session.keys():
        user=session['User']
    else:
        print("not in session")
        return
    print("got data \n\n",data)
    try:
        db=getdb(maindb)
        cur=db.cursor()
        print("got db")
        print(data['Id'],data['ChatId'])
        try:
            msg=cur.execute("select * from Message where Id=? and ChatId=?",([data['Id'],data['ChatId']])).fetchone()
           # usr=cur.execute("select * from Roommates where MateId=? and ChatId=?",([user[0],data['Chatid']])).fetchone()
            print("getting msg")
            if not msg:# and not usr:
                print("unable to get msg")
                return
            else:
                print("got msg \n",msg)
                date=datetime.now()
                date=datetime.ctime(date)
                if data['Type']=='Delete':
                    print("got delete")
                    print([user['Id'],data['Id'],date])
                    cur.execute("insert into DeletedBy(UserId,MsgId,Date) values (?,?,?)",([user['Id'],data['Id'],date]))
                    #sio.emit('managemsg',data,namespace="/chat")
                    db.commit()
                    db.close()

                    print("done deleting")
                    return
                if data['Type']=='Forward':
                    print("got forward message")
                    db.close()
                    return
                if data['Type']=='Reply':
                    print("got reply")
                    db.close()
                    return
        except:
            print("failed to get msg")
            db.rollback()
            db.close()
            return
    except:
        print("failed to get db")
        return


def getchatrooms(id):
  unreadcount=0
  chatscount=[]
  rl=[]
  try:
    print("getting db")
    db=sqlite3.connect(maindb)
    cur=db.cursor()
    print("got db")
    print("getting rooms")
    rooms=cur.execute("select * from Roommates where MateId=?",([id])).fetchall()
    #rooms=cur.execute("select c.Id,c.Name,c.Status,c.Date,c.Type from Chats as c,Roommates as r, where r.MateId=?",([id])).fetchall()
    print("got rooms")
    if not rooms:
      return "no rooms"
    print("rooms \n",rooms)
    for room in rooms:
      chatscount.append(room[3])
      croom={}
      try:
        print("getting room data for room",room[2])
        roomdata=cur.execute("select * from Chats where Id=?",([room[2]])).fetchone()
        print("got room data")
        if not roomdata:
          print("no rooms found")
          return("no rooms found")
        print("this is the room data",roomdata)
        #group into personal chats and groupchats
        croom['Id']=room[2]
        croom['Date']=roomdata[4]
        croom['Type']=roomdata[2]
        croom['Status']=roomdata[3]
        print("partial roomdata",croom)
        print(roomdata[2])
        if roomdata[2]=="Personal":
          try:
            print("getting room mate data for",room[2])
            roommate=cur.execute("select * from Roommates where ChatId=?",([room[2]])).fetchall()
            print("got roommate list")
            print(roommate)
            for i in roommate:
              print('\n i[0]',i[1])
              print('\n id',id)
              if int(i[1])==int(id):
                print("im the roommate silly")
              else:
                ##add roommate
                try:
                  print('\n i[0]',i[1])
                  print("getting roomate data")
                  rdata=cur.execute("select * from Users where Id=?",([i[1]])).fetchone()
                  ##get Names and Dp
                  print("got roommate data")
                  chatname=rdata[1]+" "+rdata[2]+" "+rdata[3]
                  croom['Chatname']=chatname
                  print("\n roommates names",chatname)
                  croom['DP']=rdata[9]
                  print("roommate db",rdata[9])
                except :
                  print("unable to get roommate data")
                  return ("unable to get roommate data")
          except :
            print("failed to get roommate id")
            return ("failed to get roommate id")
        elif roomdata[2]=="Group":
          chatname=roomdata[1]
          croom['Chatname']=chatname
        else:
          print("chatname unknwn")
      except :
        print("failed to get roomdata")
      try:
        print("getting chatroom messages")
        print("room chat",room[2])
        msgs=cur.execute("select * from Message where ChatId=?",([room[2]])).fetchall()
        print("got chatroom messages")
        if not msgs:
          print("no msgs")
          unreadcount=0
          croom['Unread']=unreadcount
        else:
          print("\n\n chatroom messsage list",msgs)
          for msg in msgs:
            print("getting unread msg count")
            print("\n mesg[4]",msg[4])
            if msg[4]!='':
              print("message read")
            unreadcount=unreadcount+1
          croom['Unread']=unreadcount
          print("unread msgs",unreadcount)
      except :
        print("unable to get unread messages")
        return("unable to get unread messages")
      print("\n\n new croooooooooooom \n\n",croom)
      rl.append(croom)
    return rl
  except :
    print("failed to get rooms")
    return ("failed to get rooms")

def ggetChatMateProfile(id):
  profile={}
  try:
    print("getting db")
    db=sqlite3.connect(maindb)
    cur=db.cursor()
    print("got db and cursor")
    try:
      print("getting mate profile")
      mate=cur.execute("select * from Users where Id=?",([id])).fetchone()
      print("got mate profile")
      if not mate:
        print("no such profile")
        return ("no such profile")
      print("\n mate profile",mate)
      print("creating dict obj for data")
      profile['Fname']=mate[1]
      profile['Mname']=mate[2]
      profile['Lname']=mate[3]
      profile['Email']=mate[4]
      profile['Phone']=mate[5]
      profile['Desc']=mate[7]
      profile['Role']=mate[8]
      profile['Dp']=mate[9]
      profile['Type']=mate[10]
      print("got profile")
      print("\n\n profile \n",profile)
      print("yaaaay")
      return profile
    except :
      print("failed to get mate profile")
      return ("failed to get mate profile")
  except :
    print("db failed")
    return ("db failed")

def chatCreate(db,cur,id):
  #get all registered users list
  status="active"
  type="Personal"
  chatid=""
  try:
    print("getting user list")
    uss=cur.execute("select * from Account").fetchall()
    print("got user list")
    if not uss:
      print("no user found")
      return redirect (url_for('home'))
    print("\n\n userlist",uss)
    for i in uss:
      print("\n\n iiiiiiii",((i[0])))
      print("userid",(id))
      if int(i[0])==int(id):
        print(i[0])
        print("thiiiiiis")
        print("this is me")
      else:
        print("\n\n iiiiiiii",((i[0])))
        print("userid",(id))
        print("getting chatid")
        chatid=int(random()*100000000)
        print("new chatid",chatid)
        try:
          date=datetime.now()
          print("creating chats \n",chatid,type,status,date)

          cur.execute("insert into Chats (Id,Type,Status,Date) values(?,?,?,?)",([chatid,type,status,date]))
          db.commit()
          try:
            print("creating roomates")
            cur.execute("insert into Roommates (MateId,ChatId) values(?,?)",([id,chatid]))
            cur.execute("insert into Roommates (MateId,ChatId) values(?,?)",([i[0],chatid]))
            db.commit()
            print("roomate success")
          except :
            db.rollback()
            print("failed to create chat roomate")

        except :
          db.rollback()
          print("failed to create new chat")

  except :
    db.rollback()
    print("failed to get user list")
    return ("failed to get user list")

def chatcreate(db,cur,id):
  #get all registered users list
  status="active"
  type="Personal"
  chatid=""
  try:
    print("getting user list")
    uss=cur.execute("select * from Accounts where Type=?",([Personal])).fetchall()
    print("got user list")
    if not uss:
      print("no user found")
      return
    print("\n\n userlist",uss)
    for i in uss:
      print("\n\n iiiiiiii",((i[0])))
      print("userid",id)
      if int(i[0])==int(id):
        print(i[0])
        print("thiiiiiis")
        print("this is me")
      else:
        print("\n\n iiiiiiii",((i[0])))
        print("userid",(id))
        print("creating chatid")
        chatid=int(random()*100000000)
        print("new chatid",chatid)
        try:
          print("creating chats")
          date=datetime.now()
          cur.execute("insert into Chats (Id,Type,Status,Date) values(?,?,?,?)",([chatid,type,status,date]))
          try:
            print("creating roomates")
            cur.execute("insert into Roommates (MateId,ChatId) values(?,?)",([id,chatid]))
            cur.execute("insert into Roommates (MateId,ChatId) values(?,?)",([i[0],chatid]))

            ###add to default groups
            db.commit()
            print("roomate success")
          except :
            db.rollback()
            print("failed to create chat roomate")
            return ("failed to create chat roomate")
        except :
          db.rollback()
          print("failed to create new chat")
          return("failed to create new chat ")
  except :
    db.rollback()
    print("failed to get user list")
    return ("failed to get user list")

@sio.on("editprofile",namespace="/myprofile")
def eprofile(data):
  print(data)
  for u in data:
    print("\n\n",data[u])
  if 'User' in session.keys():
    print("in session")
    user=session['User']
  else:
    print("not in session")
    return
  myemail=''
  mypasswd=user['Password']
  print(mypasswd)
  if data["Account"]:
    print("got in account")
    print(data['Account'])
    account=data['Account']
    db=getdb(maindb)
    cur=db.cursor()
    print("this is account",account)
    if account['password']!='' and verify_pass(user['Password'],account['password']):###replace with passwrd verification
      ##check if new password
      print(" password  verified")
      mypasswd=user['Password']
      if account['newpassword']!='':
        #getnerate new password hash and set mypasswd
        passhash = passHasher(udata['passwd'])
        if not passhash:
          print("unable to change password")
          mypasswd=user['Password']
        else:
          print("got new password")
          mypasswd=passhash
      if account['email']:
        ##check if the same or updated
        if data['Account']['email']==user['Email']:
          print("got the same email")
          myemail=account['email']
        else:
          print("changed email")
          istaken=cur.execute("select * from Account where Email=?",([account['email']])).fetchone()
          if istaken:
            print("email already taken")
            db.close()
            return "email already taken"
          else:
            print("email not taken")
            print("verifying if valid")
            myemail=account['email']
          ##check if taken and if valid and set myemail
        if myemail!='' and mypasswd!='':
          print("about to update account data")
          date=datetime.ctime(datetime.now())
          ##update data
          if data['Account']:
            print("got account \n")
            print(data['Account'])
            account=data['Account']
            try:
              name=data['Personal']['fname']+" "+data['Personal']['sname']+" "+data['Personal']['tname']
              print(name)
              cur.execute("UPDATE Account set Name=?,Email=?,Role=?,Status=?,Password=? where Id=?",([name,myemail,account['level'],account['status'],mypasswd,user['Id']]))
              db.commit()
             # ata={"Name":name,"DP":user['DP'],'Id':user['Id']}
              user['Name']=name
              session['User']=user
              print(user)
              sio.emit("mydata",user,room=request.sid,namespace="/minehome")
              print("\n updated account")
              sio.emit("updatedata",account,room=request.sid,namespace="/myprofile")
              ##emit this
            except:
              print("unable to Update account data")
              db.rollback()
              db.close()
              ###emit old values
              return "unable to Update account data"
          if data['Personal']:
            print("got personal \n")
            per=data['Personal']
            try:
              print("\n ",per)
              cur.execute("UPDATE PersonalDetails set FirstName=?,SecondName=?,ThirdName=?,FirstContact=?,SecondContact=?,Sex=?,DOB=?,MaritalStatus=?,Occupation=?,Role=? where AccountId=?",([per['fname'],per['sname'],per['tname'],per['fcontact'],per['scontact'],per['sex'],per['dob'],per['mstatus'],per['occupation'],per['role'],user['Id']]))
              db.commit()
              print("\n updated personal")
              ##emit this
              sio.emit("updatedata",per,room=request.sid,namespace="/myprofile")
            except:
              print("unable to Update personal data")
              db.rollback()
              try:
                m=cur.execute("select * from PersonalDetails where AccountId=?",([user['Id']])).fetchone()
                if not m:
                  print("no such user data need to relogin")
                  db.rollback()
                  db.close()
                  return
                else:
                  #send one at a time
                  da={"Id":m[0],"Type":'Personal',"fname":m[1],"sname":m[2],"tname":m[3],'fcontact':m[4],'scontact':m[5],'sex':m[7],'dob':m[8],'mstatus':m[9],'occupation':m[10],'role':m[11]}
                  k=list(da)
                  print(da)
                  print("\n",k)
                  da['keys']=k
                  sio.emit("updatedata",da,room=request.sid,namespace="/myprofile")
              except:
                print("unable to get old user data")
                db.close()
                return
          if data['Medical']:
            #loop and update db
            print("almost in loop")
            for md in data['Medical']:
              print("in loop")
              print("\n",md)
              print("\n",md['CMD'])
              if md['CMD']=='Update':
                try:
                  print("got update\n")
                  cur.execute("UPDATE Medical set Name=?,Desc=? where UserId=? and Id=?",([md['Name'],md['Desc'],user['Id'],md['Id']]))
                  db.commit()
                  print("\n updated medical")
                  sio.emit("updatedata",md,room=request.sid,namespace="/myprofile")
                except:
                  print("unable to Update medical data")
                  db.rollback()
                  try:
                    m=cur.execute("select * from Medical where UserId=? and Id=?",([user['Id'],mm['Id']])).fetchone()
                    if not m:
                      print("no such medical data")
                      db.rollback()
                    else:
                      da={"Id":m[0],"Type":'Medical',"Name":m[3],"Kind":m[2],'Desc':m[5]}
                      da['CMD']='Update'
                      #da=json.dumps(da)
                      print(da)
                      sio.emit("updatedata",da,room=request.sid,namespace="/myprofile")
                  except:
                    print("unable to get old med values")
              elif md['CMD']=='Create':
                try:
                  print("got create \n")
                  cur.execute("Insert into Medical (UserId,Type,Name,Date,Desc) values(?,?,?,?,?)",([user['Id'],md['Kind'],md['Name'],date,md['Desc']]))
                  db.commit()
                  print("\n created medical")
                  sio.emit("updatedata",md,room=request.sid,namespace="/myprofile")
                except:
                  print("unable to Update medical data")
                  db.rollback()
              elif md['CMD']=='Delete':
                try:
                  print("got delete\n")
                  cur.execute("Delete from Medical where Id=?",([md['Id']]))
                  db.commit()
                  print("\n deleted medical")
                  sio.emit("updatedata",md,room=request.sid,namespace="/myprofile")
                except:
                  print("unable to Update medical data")
                  db.rollback()
                  try:
                    m=cur.execute("select * from Medical where UserId=? and Id=?",([user['Id'],mm['Id']])).fetchone()
                    if not m:
                      print("no such medical data")
                      db.rollback()
                    else:
                      da={"Id":m[0],"Type":'Medical',"Name":m[3],"Kind":m[2],'Desc':m[5]}
                      da['CMD']='Update'
                      #da=json.dumps(da)
                      print(da)
                      sio.emit("updatedata",da,room=request.sid,namespace="/myprofile")
                  except:
                    print("unable to get old med values")
              else:
                print("dont know what cmd is")
          if data['Emergency']:
            print("got emerg\n")
            for em in data['Emergency']:
              print("inloop")
              print(em)
              ###use
              try:
                print("updating")
                print(user['Id'])
                cur.execute("UPDATE Emergency set Name=?,ContactOne=?,ContactTwo=?,Role=?,Member=? where UserId=? and Id=?",([em['name'],em['phone'],em['contact'],em['role'],em['member'],user['Id'],em['Id']]))
                db.commit()
                print("emer update success")
                #emit this
                sio.emit("updatedata",em,room=request.sid,namespace="/myprofile")
              except:
                print("unable to Update emergency data")
                db.rollback()
          if data['Education']:
            print("got education\n")
            print(data['Education'])
            for md in data['Education']:
              if md['CMD']=='Update':
                try:
                  print("got update\n")
                  print(md)
                  ##update the updatee
                  cur.execute("UPDATE Education set Institution=? where UserId=? and Id=?",([md['Institution'],user['Id'],md['Id']]))
                  db.commit()

                  sio.emit("updatedata",md,room=request.sid,namespace="/myprofile")
                  print("\n updated education")
                except:
                  print("unable to Update education data")
                  db.rollback()
                  try:
                    m=cur.execute("select * from Education where Id=?",([md['Id']])).fetchone()
                    if not m:
                      print("no such medical data")
                      db.rollback()
                    else:
                      da={"Id":m[0],"Institution":m[2],"Level":m[3],'Type':'Education'}
                      da['CMD']='Update'
                      #da=json.dumps(da)
                      print(da)
                      sio.emit("updatedata",da,room=request.sid,namespace="/myprofile")
                  except:
                    print("unable to get old med values")
              if md['CMD']=='Create':
                print("got create \n")
                print(md)
                try:
                  ##create
                  cur.execute("Insert into Education (UserId,Institution,Level,Date) values(?,?,?,?)",([user['Id'],md['Institution'],md['Level'],date]))
                  db.commit()
                  sio.emit("updatedata",md,room=request.sid,namespace="/myprofile")
                  print("\n created education")
                except:
                  print("unable to Update education data")
                  db.rollback()
              if md['CMD']=='Delete':
                try:
                  print("got delete\n")
                  print(md)
                  print(md['Id'])
                  if db:
                    print("still got it")
                  else:
                    print("dont got it")
                  cur.execute("DELETE from Education where Id=?",([md['Id']]))
                  db.commit()
                  sio.emit("updatedata",md,room=request.sid,namespace="/myprofile")
                  print("\n deleted education")
                except:
                  print("unable to Update education data")
                  db.rollback()
                  try:
                    m=cur.execute("select * from Education where Id=?",([md['Id']])).fetchone()
                    if not m:
                      print("no such medical data")
                      db.rollback()
                    else:
                      da={"Id":m[0],"Institution":m[2],"Level":m[3],'Type':'Education'}
                      da['CMD']='Update'
                      #da=json.dumps(da)
                      print(da)
                      sio.emit("updatedata",da,room=request.sid,namespace="/myprofile")
                  except:
                    print("unable to get old med values")
                  ###query old values
        else:
          print("no email")
          db.rollback()
          db.close()
          return "no email"
    else:
      print("password does not verify")
      db.rollback()
      db.close()
      return "password does not verify"
  return

@sio.on("tprofile",namespace="/userprofile")
def editprofile(data):
  print("got profile edit data")
  print(data)
  user=''
  if 'User' in session.keys():
    print("in session")
    user=session['User']
  else:
    print("not in session")
  if data['Account']:
    acc=data['Account']

@app.route('/Editprofile',methods=['POST'])
def Editprofile():
  session['userid']=108824877907
    ###list items
  sname = ""
  fname=""
  tname = ""
  email = ""
  pnumber1 = ""
  level = ""
  pic = ""
  ilist=['fname','sname','email','pnumber1','level','pic']
  udata={}
  if not session['userid']:
    print("must relogin")
    return ("must relogin")
  #else get user data
  userid=session['userid']
  if request.method == "POST":
      c=request.values
      print(c)
      for i in c:
        #print(i)
        #print(c[i])
        s=i.strip(' ')
        #print(s)
        udata[s]=c[i]
        if s in ilist:
          print(c[i])
          s=c[i]
          print(s)
      print(udata)
      print(type(udata))
      if udata['fname']=="" or udata['sname']=="" or udata['tname']=="" or udata['email']=="" or udata['oldpasswd']=="":
        print("missing data")
        return "missing data"
      ####data type validator
      #if not EmailValidator(email):
      #    print("email does not verify")
      #print("email does verify")

      if not pic=="":
        print('\n\n piccccccc',pic)
        dpname=saveDp(pic)
        print('\n\n dpnaaaaaaame',dpname)
        if dpname!=False:
          pic=dpname
          udata['pic']=pic
        else:
          pic=""
          udata['pic']=pic
      else:
        print("no dp provided")
        pic=""
        udata['pic']=pic
      try:
        email=udata['email']
        print("eeemail")
        print(email)
        print("getting db")
        db = getdb(maindb)
        print("got db")
        print("dbbbbbb", db)
        print("getting cursur")
        cur = db.cursor()
        print("got cursur")
        user=cur.execute('select * from Users where Id=?',([userid])).fetchone()
        print(user[4])
        if udata['email']!=user[4]:#old email
          print("got new Email")
          gube=getUserByEmail(cur,udata['email'])
          print("gubee\n\n")
          print(gube)
          if gube:
            print("user already has email")
            return ("email already taken")
          print("email ready for use")
        else:
          print("using old email")
        if udata['newpasswd']!="":
          print("got new password")
          ##check old password
          if udata['oldpasswd']!="":
            #confirm password is valid
            print(user[13])
            if not check_password_hash(user[13],udata['oldpasswd']):
              print("old password does not match")
              return ("invalid password")
            else:
              passhash = passHasher(udata['newpasswd'])
              if not passhash:
                print("failed to generate password hash")
                return "failed to hash password"
              print("got password hash")
              print("got password hash")
              udata['passwd']=passhash
        else:
          print("got old password")
          if not check_password_hash(user[13],udata['oldpasswd']):
              print("old password does not match")
              return ("invalid password")
          print(user[13])
          udata['passwd']=user[13]
        try:
          date=datetime.now()
          ####gen user id
          print("confirm user data",udata)
          print(userid)
          cur.execute("UPDATE Users set FirstName=?,MiddleName=?,LastName=?,Email=?,Phone1=?,Dp=?,Type=?,PassHash=?,Date=? where Id=?",(udata['fname'],udata['sname'],udata['tname'],udata['email'],udata['level'],udata['pic'],udata['phone'],udata['passwd'],date,userid))
          print("user update success")
          db.commit()
          cur.close()
          return "update sucessful"
        except:
        ####check for id error
          print("failed to add user")
          db.rollback()
          cur.close()
          db.close()
          ###send verification token t o user email with login link
          return "failed"
      except:
          print("failed to get cursor")
          return "failed to get cursor"
  else:
    return "use get"

@app.route('/gchat/<Id>')
def gchat(Id):
  return render_template('gchat.html',Id=Id)

@sio.on("groupusers",namespace="/group")
def groupusers(data):
  print("got group id",data)
  user=""
  ml=[]
  if 'User' in session.keys():
    user=session['User']
  else:
    print("not in session")
    return
  try:
    db=getdb(maindb)
    cur=db.cursor()
    print("got db")
    try:
      ##get groupmates
      ing=cur.execute("select * from Roommates where MateId=? and ChatId=?",([user['Id'],data])).fetchone()
      if not ing:
        print("not in group")
        db.close()
        return
      else:
        print("in group getting mates")
        mates=cur.execute("select * from Roommates where ChatId=?",([data])).fetchall()
       # mates=list(mates)
        if mates:
          print("got mates",mates)
          for d in mates:
            print(d[1])
            ml.append(d[1])
        else:
          print("no mates")
          db.close()
          return
        md=cur.execute("select * from Account").fetchall()
        for m in md:
          print("current id \n",m[0],mates)
          mdata={
                "Id":m[0],
                "Name":m[1],
                "Dp":m[3],
                "MyId":user['Id'],
                "Level":user['Role']
             }
          if m[0] in ml:
            mdata['Member']="true"
            print("got member \n",mdata)
            sio.emit("groupusers",mdata,room=request.sid,namespace="/group")
          else:
            mdata['Member']='false'
            print("got non member \n",mdata)
            sio.emit("groupusers",mdata,room=request.sid,namespace="/group")
        db.close()
        return
    except:
      print("unable to get members")
      db.close()
      return
  except:
    print("unable to get db and cursor")
    return

@sio.on("joingroup",namespace="/group")
def join(cdata):
  chatid=cdata
  user=session['User']
  userid=user["Id"]
  print("joining",chatid)
  try:
    db=getdb(maindb)
    cur=db.cursor()
    print("got db")
    rrm=cur.execute("select * from Chats where Id=?",([chatid])).fetchone()
    ###get
    ct=cur.execute("select * from Roommates where ChatId=? and MateId=?",([chatid,userid])).fetchone()
    if not ct and rrm:
      return "not in this chat"
    else:
      print("in group")
      c=str(chatid)
      join_room(c,namespace="/group")
      print(rrm)
      print("joined group")

      mdata=cur.execute("select * from Groups where Id=?",([rrm[4]])).fetchone()
      if not mdata:
        print("no group records")
        return
      print("got group data")
      data={'Name':mdata[1],'Dp':mdata[5],'Id':mdata[0]}
      ##emit this
      print(data)
      sio.emit("mydata",data,room=request.sid,namespace="/group")
      print("\n getting messages for group",chatid)
      msgs=cur.execute("select * from Message where ChatId=?",([chatid])).fetchall()
      print("\n\n got messages for group",chatid)
      if not msgs:
        print("no messages")
        return ("no messages")
      print("\n\n messages for group",msgs)
      for msg in msgs:
        ###return dictionary obj
        ####get commentor
        print("\n\n getting creator")
        cmt=cur.execute("select * from Account where Id=?",([msg[1]])).fetchone()
        if not cmt:
          print("no commentor")
          print("\n no author found")
          pass
        else:
          print("\n author found")
          mmsg={
                "Id":msg[0],
                "Msg":msg[3],
                "SentDate":msg[5],
                "ReatAt":msg[7],
                "UserId":msg[1],
                "Delivered":msg[6],
                "Status":msg[4],
                "MyId":userid,
                "Dp":cmt[3],
                "UserName":cmt[1],
                }
          print("message object")
          print(mmsg)
          sio.emit("recvmsg",mmsg,room=request.sid,namespace="/group")
          try:
            print("getting attatchments")
            print("getting attatchment for message id",msg[0])
            msgatt=cur.execute("select * from MessageAtt where MessageId=?",([msg[0]])).fetchall()
            print("got attatchment")
            if not msgatt:
              print("no attatchment")
            else:
              print("atttchment list for message",msgatt)
              for i in msgatt:

                mat={}
                mat['Id']=i[0]
                mat['Name']=i[1]
                mat["Type"]=i[3]
                mat["MsgId"]=msg[0]
                mat["ChatId"]=chatid
                print("message object")
                print(mat)
              print("message object")
              print(mmsg)
              sio.emit("recvatt",mat,room=request.sid,namespace="/group")
              ##emit here
          except :
            print("failed to get messages attatchments")
            return("failed to get messages attatchments")
      db.close()
      return "joined"
  except:
    db.close()
    return "db failed"

def  getGroupMessagesData(chatid):
  mymsg={}
  attl=[]
  try:
    print("getting db")
    db=sqlite3.connect(maindb)
    cur=db.cursor()
    print("got db and cursor")
    try:
      m=cur.execute("select * from Groupmate where GroupId=? and MateId=?",([])).fetchone()
      if not m:
        print("not allowed in this room")
        return
      print(m)
      mdata=cur.execute("select * from Groups where Id=?",([])).fetchone()
      if not mdata:
        print("no group records")
        return
      data={'Name':mdata[1],'Dp':mdata[5],'Id':mdata[0]}
      ##emit this
      print("\n getting messages for group",chatid)
      msgs=cur.execute("select * from Message where ChatId=?",([chatid])).fetchall()
      print("\n\n got messages for group",chatid)
      if not msgs:
        print("no messages")
        return ("no messages")
      print("\n\n messages for group",msgs)
      for msg in msgs:
        ###return dictionary obj
        print("creating msg dict obj")
        mymsg["Id"]=msg[0]
        mymsg["msg"]=msg[3]
        print("\n message",msg[3])
        mymsg["sentDate"]=msg[5]
        mymsg["DeliveredDate"]=msg[6]
        mymsg["Status"]=msg[4]
        mymsg["ReadAt"]=msg[7]
        mymsg['UserId']=msg[1]
        ####get commentor
        cmt=cur.execute("select * from Users where Id=?",([msg[1]])).fetchone()
        if not cmt:
          print("no commentor")
          pass
        else:
          try:
            print("getting attatchments")
            print("getting attatchment for message id",msg[0])
            msgatt=cur.execute("select * from MessageAtt where MessageId=?",([msg[0]])).fetchall()
            print("got attatchment")
            if not msgatt:
              print("no attatchment")
            else:
              print("atttchment list for message",msgatt)
              for i in msgatt:
                mat={}
                mat['Id']=i[0]
                mat['Name']=i[1]
                mat["Size"]=i[3]
                print("getting attatchment attributes for message id",msg[0])
              print("\n\n my messages",mymsg)
              ##emit here
          except :
            print("failed to get messages attatchments")
            return("failed to get messages attatchments")
      return mymsg
    except :
        cur.close()
        db.close()
        print("failed to get messages ")
        return("failed to get messages a")
  except :
        print("failed to get db ")
        return("failed to get db")

@sio.on("msg",namespace="/group" )
def hanack(da):
  print(da)
  print(rooms())
  for i in rooms():
    print(i,type(i))
  rm=str(da['GroupId'])
  c=request.sid
  print("got data")
  print(c)
  date=datetime.now()
  dd={}
  user=session['User']
  userid=user['Id']
  ss=type(date)
  print(ss)
  try:
    print("getting db")
    db=getdb(maindb)
    cur=db.cursor()
    chatid=da['GroupId']
    cc=cur.execute("select * from Roommates where ChatId=? and MateId=? and Status=?",([chatid,userid,"Active"])).fetchone()
    print(cc)
    if cc:
      chatid=da['GroupId']
      mssg=da['Msg']
      date=datetime.ctime(datetime.now())
      print("inserting")
      print(userid,chatid,mssg,type(date))
      msid=int(random()*10000000000)
      cur.execute("insert into Message (Id,UserId,ChatId,Message,Status,SentDate) values(?,?,?,?,?,?)",(msid,userid,chatid,mssg,'Active',date))
      db.commit()
      db.close()
      da['SentDate']=date
      da['Userid']=userid
      da['Id']=msid
      print("message saved")
      if 'File' in da:
        print("got file")
        print("got file")
        sio.emit('recvmsg',da,room=rm,namespace="/group")
        td.run(addfile(da,msid,userid))
      else:
        print("no file")
        sio.emit('recvmsg',da,room=rm,namespace="/group")
        print("got no file")
  except:
    print("db error")
    db.close()
    return "db error"

@app.route('/group/<groupid>/')
def group(groupid):
  userid=''
  groupid=groupid
  print(type(groupid))
  if not groupid:
    return redirect (url_for('getMessangerhome'))
  if 'User' in session.keys():
    user=session['User']
    userid=user[0]
    print("sooooooooooooo this is my userid",userid)
  if not userid:
    print("not in session")
    return "redirect to login"
  print("im in session")
  if not groupid:
    return ("no data")
  print("\n\n\n\n\n\n chatdta")
  dd=str(groupid)
  join_room(dd)
  chatdata= getGroupProfile(userid,groupid)
  if not chatdata:
    print("no data")
    chatdata={}
    return render_template('messanger.html',groupdata=chatdata)
  else:
    print("chatdata",chatdata)
    Groupuser=chatdata['Groupuser']
    Groupchat=chatdata['Groupchat']
    Groupdata=chatdata['Groupdata']
    myname=user[1]+" "+user[2]+" "+user[3]
    Mydata={"Id":user[0],'Username':myname,"Member":"True","DP":user[9]}
    try:
      print("getting db on update")
      db=getdb(maindb)
      cur=db.cursor()
      date=datetime.ctime(datetime.now())
      print("got db about to update")
      cur.execute("UPDATE Message set ReadAt=? where ChatId=?",([date,groupid]))
      cur.execute("UPDATE Message set DeliveredDate=? where ChatId=?",([date,groupid]))
      db.commit()
      db.close()
      print("update succcessful")
    except:
      db.rollback()
      db.commit()
      print("no update")
    return render_template("groupMessager.html",Groupuser=Groupuser,Groupchat=Groupchat,Groupdata=Groupdata,Mydata=Mydata)
  #######get groupchat messages on getgroupmate profile

@sio.on("joinnotif",namespace="/minehome")
def joinnotif(da):
  print(da)
  ##get rooms groups and unread message count
  user=getUser()
  if 'User' in session.keys():
    print("in session")
    print(session['User'])
    #emit this
    user=session['User']
    username=user['Name']
    data={"Name":username,"DP":user['DP'],'Id':user['Id']}
    sio.emit("mydata",user,room=request.sid,namespace="/minehome")
  else:
    print("not in session")
    #send redirect command
    return
  userid=user['Id']
  try:
    db=getdb(maindb)
    cur=db.cursor()
    print("got db")
    try:
      print("getting groups \n")
      chats=cur.execute("select * from Roommates where MateId=?",([userid])).fetchall()
      ##select * from accounts roomates
      print("got chats and groups")
      if chats:
        print("got chats \n")
        print(chats)
        for chat in chats:
          sid=request.sid
          print(sid)
          sx=str(chat[2])
          join_room(sx,sid=sid,namespace="/minehome")
          print("joined room",chat[2])
          ###check if group or chat
          try:
            chatmate=cur.execute("select * from Chats where Id=?",([chat[2]])).fetchone()
            if not chatmate:
              print("no mate found \n")
            else:
              print(" got chatmate \n")
              print(" getting chatmate data \n")
              print(chatmate)
              print(chatmate[1])
              chatdata=''
              data=''
              ####check if group or personal    ///jesus im good at this
              if chatmate[1]=='Group':
                chatdata=cur.execute('select * from groups where Id=?',([chatmate[4]])).fetchone()
                if not chatdata:
                  print("chat mate data not found")
                else:
                  print(" got chatmate data \n")
                  print(chatdata)
                  usern=chatdata[1]
                  data={"Name":chatdata[1],"Id":chatmate[0],"dp":chatdata[3],'Type':"Group"}
                  print(data)
                  sio.emit("chatdata",data,room=request.sid,namespace="/minehome")
                  try:
                    print("chatid",id[2])
                    msg=cur.execute("select * from Message where ChatId=?",([chat[2]])).fetchall()###replace with query count
                    if not msg:
                      print("no mesages")
                      data['Type']='Unread'
                      data['Unread']=0
                      sio.emit("chatdata",data,room=request.sid,namespace="/minehome")
                      ###emit this
                    else:
                      print("message length",len(msg))
                      c=len(msg)
                      data['Unread']=c
                      data['Type']='Unread'
                      print(data)
                      sio.emit("chatdata",data,room=request.sid,namespace="/minehome")
                      ###emit this
                  except:
                    print("failed to get messages")
              if chatmate[1]=='Personal':
                print("\n in personal")
                print("\n",chat[2],userid)
                roommate=cur.execute("select * from Roommates where ChatId=? and MateId!=?",([chat[2],userid])).fetchone()
                if roommate:
                  print("\n got roommate")
                  chatdata=cur.execute("select * from Account where Id=?",([roommate[1]])).fetchone()
                  if not chatdata:
                    print("chat mate data not found")
                  else:
                    print(" got chatmate data \n")
                    print(chatdata)
                    usern=chatdata[1]
                    data={"Name":chatdata[1],"Id":chatmate[0],"dp":chatdata[3],'Type':"Chat"}
                    print(data)
                    sio.emit("chatdata",data,room=request.sid,namespace="/minehome")
                    try:
                      print("chatid",id[2])
                      msg=cur.execute("select * from Message where ChatId=?",([id[2]])).fetchall()###replace with query count
                      if not msg:
                        print("no mesages")
                        data['Type']='Unread'
                        data['Unread']=0
                        sio.emit("chatdata",data,room=request.sid,namespace="/minehome")
                        ###emit this
                      else:
                        print("message length",len(msg))
                        c=len(msg)
                        data['Unread']=c
                        data['Type']='Unread'
                        print(data)
                        sio.emit("chatdata",data,room=request.sid,namespace="/minehome")
                        ###emit this
                    except:
                      print("failed to get messages")
          except:
            print("failed to get chat mate")
      else:
        print("no chats")
        ###emit this
    except:
      db.close()
      print("query failed")
      return "db failed"
  except:
    print("db failed")
    return "db failed"

@app.route('/chat/<chatid>/')
def chat(chatid):
  ##given chat id,,get roomates data........name,dp,id
  ###get chat messages and files
  ###
  print("returning chat page")
  print(chatid)
  userid=''
  print(session.keys())
  if 'User' in session.keys():
    user=session['User']
    userid=user[0]
  if not userid:
    print("not in session")
    return "redirect to login"
  if not chatid:
    return redirect (url_for('getMessangerhome'))
  print("\n\n\n\n\n\n chatdta")
  cx=str(chatid)
  join_room(cx)
  chatdata=getChatMateProfile(userid,chatid)
  print('chatdata')
  if not chatdata:
    print("no data")
    chatdata={}
    return render_template('messanger.html',chatdata=chatdata)
  else:
    try:
      print("getting db on update")
      db=getdb(maindb)
      cur=db.cursor()
      date=datetime.ctime(datetime.now())
      print("got db about to update")
      ##and userid is not mine
      cur.execute("UPDATE Message set ReadAt=? where ChatId=?",([date,chatid]))
      cur.execute("UPDATE Message set DeliveredDate=? where ChatId=?",([date,chatid]))
      db.commit()
      db.close()
      print("update succcessful")
    except:
      db.rollback()
      db.commit()
      print("no update")
    print("chatdata",chatdata)
    Matedata=chatdata['Matedata']
    Mydata=chatdata['Mydata']
    Chatdata=chatdata['Chatdata']
    print(Chatdata)
    return render_template('messanger.html',chatdata=Chatdata,Matedata=Matedata,Mydata=Mydata,chatid=chatid)

  ###getchatmessages on chatmate profile

def getChatMateProfile(id,chatid):
  allprofile=[]
  Matedata={}
  Mydata={}

  ###
  allmsgs=[]
  try:
    print("getting db")
    db=sqlite3.connect(maindb)
    cur=db.cursor()
    print("got db and cursor")
    try:
      print("getting mate id from roommate data")
      chat=cur.execute("select * from Chats where Id=?",([chatid])).fetchone()
      if not chat:
        print("no such chatroom")
        return False
      print("chats",chat)
      mates=cur.execute("select * from Roommates where chatId=?",([chatid])).fetchall()
      if not mates:
        print("no mates data")
        return False
      print("mate data",mates)
      for mate in mates:
        try:
          matedata=cur.execute("select * from Users where Id=?",([mate[1]])).fetchone()
          if not matedata:
            print ("user data error")
            return False
          if matedata[0]==id:
            profile={}
            profile['Id']=matedata[0]
            print("got profile")

            profile['Username']=matedata[1]+' '+matedata[2]+' '+matedata[3]
            profile['Email']=matedata[4]
            profile['Phone']=matedata[5]

            profile['Role']=matedata[8]
            profile['Dp']=matedata[9]
            profile['Type']=matedata[10]
            profile['Chatid']=chatid
            print("got profile")
            print("\n\n profile \n",profile)
            print("yaaaay")
            Mydata=profile
          else:
            print("getting second person data")
            profile={}
            profile['Id']=matedata[0]
            profile['Username']=matedata[1]+' '+matedata[2]+' '+matedata[3]
            profile['Email']=matedata[4]
            profile['Phone']=matedata[5]
            profile['Role']=matedata[8]
            profile['Dp']=matedata[9]
            profile['Type']=matedata[10]
            print("got profile")
            print("\n\n profile \n",profile)
            print("yaaaay")
            Matedata=profile
        except :
          print("failed to get mate profile")
          return ("failed to get mate profile")
      print("getting messages",chatid)
      try:
        msgs=cur.execute("select * from Message where ChatId=? ORDER BY SentDate",([chatid])).fetchall()
        if not msgs:
          print("no messages")
        else:
          print(msgs)

          for msg in msgs:
            ###check deletedby
            cd=cur.execute("select * from DeletedBy where MsgId=? and UserId=?",([msg[0],id])).fetchone()
            if cd:
              print("message deleted by me")
            else:
              msgatt=[]
              print('this is the msg',msg)
              ms={'Id':msg[0],'Message':msg[3],'Userid':msg[1],'Chatid':msg[2],"Status":msg[4],'Sent':msg[5],'Delivered':msg[6]}
              atts=cur.execute("select * from MessageAtt where MessageId=?",([msg[0]])).fetchall()
              if not atts:
                ms['Att']=""
              else:
                for att in atts:

                  Att={'Name':att[1],'Id':att[0],'MessageId':att[2],'Type':att[3]}
                  msgatt.append(Att)
                ms["Att"]=msgatt


              print(ms)
              allmsgs.append(ms)
              print("this is all for noe",allmsgs)

      except :
        print("failed to get attatch")

      print("done appending")
      data={'Matedata':Matedata,'Chatdata':allmsgs,'Mydata':Mydata}
      print("return data",data)
      return data
    except :
      print("failed to get mate profile")
      return ("failed to get mate profile")
  except :
    print("db failed")
    return ("db failed")

def getGroupProfile(id,groupid):
  allprofile=[]
  allmsgs=[]
  gdata={}
  mydata={}
  myatts=[]
  groupid=groupid
  print("input data",id,groupid)
  try:
    print("getting db")
    db=sqlite3.connect(maindb)
    cur=db.cursor()
    print("got db and cursor")
    try:

      print("getting group data for",groupid)
      gdata=cur.execute("select * from Groups where Id=?",([groupid])).fetchone()
      if not gdata:
        print("no group data")
        cur.close()
        db.close()
        print('no gdata')
        gdata={}
      else:
        print("this is the group data",gdata)
        gdata={'Id':gdata[0],'Name':gdata[1],'Status':gdata[2],'UserId':gdata[3],'Date':gdata[4],'DP':gdata[5]}
        print(gdata)
        print("getting messages")
        ####do not get msgs ifnot in group
        print("\n\n",groupid,id)
        ing=cur.execute("select * from Groupmate where GroupId=? and MateId=? and Status=?",([groupid,id,'Active'])).fetchone()
        if not ing:
          print("no longer in group")
        else:
          msgs=cur.execute("select * from Message where ChatId=? ORDER BY SentDate",([groupid])).fetchall()
          if not msgs:
            print("no messages")
            allmsgs=[]
          else:
            for msg in msgs:
              cd=cur.execute("select * from DeletedBy where MsgId=? and UserId=?",([msg[0],id])).fetchone()
              if cd:
                print("message deleted by me")
              else:
                my=[]
                ###given message find creator data
                print("got msg",msg)
                try:
                  ##get message crator
                  print("getting message creator",msg[1])
                  atts=cur.execute("select * from MessageAtt where MessageId=?",([msg[0]])).fetchall()
                  if not atts:
                    print("no atts")
                  else:
                    for tt in atts:
                      mtt={"Id":tt[0],"Name":tt[1],"Type":tt[3]}
                      my.append(mtt)
                  credata=cur.execute("select * from Users where Id=?",([msg[1]])).fetchone()
                  if not credata:
                    print("no creator"  )
                    pass
                  else:
                    print("got creator",credata)
                    username=credata[1]+' '+credata[2]+' '+credata[3]
                    print(username)
                    ms={'Id':msg[0],'Message':msg[3],'Userid':msg[1],'Chatid':msg[2],"Status":msg[4],'Sent':msg[5],'Delivered':msg[6],'Username':username,'DP':credata[9],"Att":my}
                    allmsgs.append(ms)
                except :
                  print("unable to get msg data for",msg)
          print("getting group mates")
          allusers=cur.execute("select * from Users").fetchall()
          if not allusers:
            print("no user found")
          else:
            for us in allusers:
              print(groupid,us[0])
              mates=cur.execute("select * from Groupmate where GroupId=? and MateId=?",([groupid,us[0]])).fetchone()
              if not mates:
                print('not in group')
                username=us[1]+" "+us[2]+" "+us[3]
                matedata={"Id":us[0],"Username":username,"Member":"False","DP":us[9]  }
                allprofile.append(matedata)
              else:
                username=us[1]+" "+us[2]+" "+us[3]
                print("in group")
                matedata={"Id":us[0],"Username":username,"Member":"True","DP":us[9]}
                allprofile.append(matedata)

      print("getting group messages")

      data={'Groupuser':allprofile,'Groupchat':allmsgs,'Groupdata':gdata,'Mydata':mydata}
      print("return data",data)
      return data
    except :
      print("failed to get group profile")
      return {}
  except :
    print("failed to get db")
    return False

@sio.on("adduser",namespace="/group")
def addGroupUser(data):
  user=session['User']
  print(user)
  myid=user['Id']
  print(data)
  groupid=data['Groupid']
  userid=data['Userid']
  if not userid and groupid:
    return "failed"
  try:
    print("getting db")
    db=getdb(maindb)
    cur=db.cursor()
    print("got db")
    try:
      date=datetime.ctime(datetime.now())
      if user['Role']=='Admin':
        #cur.execute("insert into Groupmate (MateId,GroupId,Date) values(?,?,?)",([userid,groupid,date]))
        cur.execute("Insert into Roommates (MateId,ChatId) values (?,?)",([userid,groupid]))
        db.commit()
        db.close()
        print("addition success")
        ###add to room
        return "True"
      else:
        print("no allowed to add users")
        db.close()
        return
    except:
      print("unable to add user to group")
      db.close()
      db.rollback()
      return "Failed"
  except:
    print("unable to get db")
    return "Failed"

@sio.on("removeuser",namespace="/group")
def removeGroupUser(data):
  print(data)
  user=session['User']
  myid=user['Id']
  groupid=data['Groupid']
  userid=data['Userid']
  if not userid and groupid:
    return "failed"
  try:
    print("getting db")
    db=getdb(maindb)
    cur=db.cursor()
    print("got db")
    try:
      date=datetime.ctime(datetime.now())
      print(userid,myid,groupid)
      if myid==userid:
        print("im leaving")
        #cur.execute("Delete From Groupmate where MateId=? and GroupId=?",([userid,groupid]))
        cur.execute("Delete From Roommates where MateId=? and ChatId=?",([userid,groupid]))
        db.commit()
        db.close()
        print("removal success")
        return "True"
      else:
        print("removing other")
        if user['Role']=='Admin':
          print("got admin")
          #cur.execute("Delete from Message where UserId=? and ChatId=?",([userid,groupid]))
          #cur.execute("Delete From Groupmate where MateId=? and GroupId=?",([userid,groupid]))
          cur.execute("DELETE from Roommates where MateId=? and ChatId=?",([userid,groupid]))
          db.commit()
          db.close()
          print("removal success")
          return "True"
        else:
          db.commit()
          db.close()
          print("no allowed to remove")
          return ""
    except:
      print("unable to add user to group")
      db.rollback()
      db.close()
      return "Failed"
  except:
    print("unable to get db")
    return "Failed"

@app.route('/myprofile')
def myprofile():
  print(session.keys())
  if 'User' in session.keys():
    return redirect(url_for('getMessangerhome'))
  else:
    #autoLogin()
    if 'User' in session.keys():
      return redirect(url_for('getMessangerhome'))
    else:
      return redirect(url_for('s'))

def getGroups(cur,id):
  allgs=[]
  print('this is my',id)
  try:
    print("getting group data")
    glist=cur.execute("select * from Groupmate where MateId=?",[id]).fetchall()
    if not glist:
      return []
    print("glist",glist)
    for g in glist:
      print("getting details for group",g)
      print(g[2])
      dd=g[2]
      gd=cur.execute("select * from Groups where Id=?",([dd])).fetchone()
      if not gd:
        print("no details for",gd)
      else:
        print(gd)
        grd={}
        grd["Id"]=gd[0]
        grd["Name"]=gd[1]
        grd["Status"]=gd[2]
        grd["Date"]=gd[4]
        grd['DP']=gd[5]
        print(grd)
        allgs.append(grd)
    return allgs
  except :
    print("unable to get grouplist and group data")
    return False

@sio.on('createG',namespace="/minehome")
def createG(data):
  print(data)
  id=''
  user=''
  if not 'User' in session.keys():
    #try relogin
    #autoLogin()
    if not 'User' in session.key():
      return "relogin"
    else:
      user=session['User']
      id=user['Id']
      print("user id",id)
  else:
    user=session['User']
    id=user['Id']
    print("user id",id)
    try:
      print("getting db")
      db=getdb(maindb)
      cur=db.cursor()
      print("got db")
      try:
        date=datetime.ctime(datetime.now())
        print("inserting group data",data['Name'])
        print(id)
        gid=int(random()*10000000000)
        chatid=int(random()*10000000000)
        cur.execute("Insert into Groups (Id,Name,Status,UserId,Date) values (?,?,?,?,?)",([gid,data['Name'],'Active',id,date]))
        print("created group")
        cur.execute("Insert into chats (Id,Type,Status,Date,AccountId) values (?,?,?,?,?)",([chatid,'Group','Active',date,gid]))
        print("created chat")
        cur.execute("Insert into Roommates (MateId,ChatId) values (?,?)",([id,chatid]))
        for d in data:
          if 'user' in d:
            print(d)
            cur.execute("Insert into Roommates (MateId,ChatId) values (?,?)",([data[d],chatid]))
            print("created roommate",data[d],d)
        db.commit()
        db.close()
        return redirect(url_for('Mhome'))
      except:
        print("unable to add to db")
        db.rollback()
        db.close()
        return redirect(url_for('Mhome'))
    except :
      print("db error")
      return redirect(url_for('Mhome'))

def getchatrooms(cur,id):
  unreadcount=0
  roomss=[]
  try:
    print("getting rooms")
    rooms=cur.execute("select * from Roommates where MateId=?",([id])).fetchall()
    #rooms=cur.execute("select c.Id,c.Name,c.Status,c.Date,c.Type from Chats as c,Roommates as r, where r.MateId=?",([id])).fetchall()
    print("got rooms")
    if not rooms:
      return []
    print("rooms \n",rooms)
    for room in rooms:
      croom={}
      try:
        print("getting room data for room",room[2])
        roomdata=cur.execute("select * from Chats where Id=?",([room[2]])).fetchone()
        print("got room data")
        if not roomdata:
          print("no rooms found")
          return("no rooms found")
        print("this is the room data",roomdata)
        #group into personal chats and groupchats
        croom['Id']=room[2]
        croom['Date']=roomdata[4]
        croom['Type']=roomdata[2]
        croom['Status']=roomdata[3]
        print("partial roomdata",croom)
        print(roomdata[2])
        try:
          print("getting room mate data for",room[2])
          roommate=cur.execute("select * from Roommates where ChatId=?",([room[2]])).fetchall()
          print("got roommate list")
          print(roommate)
          if not roommate:
            print("no roomates have been created")
            roomss=[]
            return roomss
          for i in roommate:
            print('\n i[0]',i[1])
            print('\n id',id)
            if int(i[1])==int(id):
              print("im the roommate silly")
            else:
              ##add roommate
              try:
                print('\n i[0]',i[1])
                print("getting roomate data")
                rdata=cur.execute("select * from Users where Id=?",([i[1]])).fetchone()
                ##get Names and Dp
                if not rdata:
                  print("did not get user data")
                else:
                  print("got roommate data")
                  chatname=rdata[1]+" "+rdata[2]+" "+rdata[3]
                  croom['Chatname']=chatname
                  print("\n roommates names",chatname)
                  croom['DP']=rdata[9]
                  print("roommate db",rdata[9])
              except :
                print("unable to get roommate data")
                return ("unable to get roommate data")
        except :
          print("failed to get roommate id")
          return ("failed to get roommate id")
      except :
        print("failed to get roomdata")
      try:
        print("getting chatroom messages")
        print("room chat",room[2])
        msgs=cur.execute("select * from Message where ChatId=?",([room[2]])).fetchall()
        print("got chatroom messages")
        if not msgs:
          print("no msgs")
          unreadcount=0
          croom['Unread']=unreadcount
        else:
          print("\n\n chatroom messsage list",msgs)
          for msg in msgs:
            print("getting unread msg count")
            print("\n mesg[4]",msg[4])
            if msg[7]==None and msg[1]!=id:
              unreadcount=unreadcount+1
            else:
               print("message read")
          croom['Unread']=unreadcount
          print("unread msgs",unreadcount)
      except :
        print("unable to get unread messages")
        return("unable to get unread messages")
      roomss.append(croom)
      print("\n\n\n rmsssssssssssssss \n\n")
    return roomss
  except :
    print("failed to get rooms")
    return ("failed to get rooms")


@app.route('/signup',methods=['POST'])
def signup():
    ###list items
    sname = ""
    fname=""
    tname = ""
    email = ""
    pnumber1 = ""
    level = ""
    pic = ""
    ilist=['fname','sname','email','pnumber1','level','pic']
    udata={}
    if request.method == "POST":
        c=request.values
        x=request.files
        print(x)
        for i in c:
          #print(i)
          #print(c[i])
          s=i.strip(' ')
          #print(s)
          udata[s]=c[i]
          if s in ilist:
            print(c[i])
            s=c[i]
            print(s)
        print(udata)
        print(type(udata))
        if udata['fname']=="" or udata['sname']=="" or udata['tname']=="" or udata['email']=="" or udata['passwd']=="":
          print("missing data")
          return "missing data"
        ####data type validator
        #if not EmailValidator(email):
        #    print("email does not verify")
        #print("email does verify")
        passhash = passHasher(udata['passwd'])
        if not passhash:
            print("failed to generate password hash")
            return render_template("signup.html",udata=udata)
        print("got password hash")
        print("got password hash")
        udata['passwd']=passhash
        if x:
          picc=request.files['pic']
          print('got profile  file obj',picc)
          dpname=secure_filename(picc.filename)
          if dpname:
            ss=dpname.rindex(".")
            nn="mydp"+str(int(random()*100000000))
            pcname=nn+dpname[ss:]
            udata['pic']=pcname
            picc.save('./static/Images/DP/'+pcname)
            print('\n\n dpnaaaaaaame',dpname)
          else:
            print("failed to get file name")
            udata['pic']=""
        else:
          print("no dp provided")
          udata['pic']=""
        try:
            email=udata['email']
            print("eeemail")
            print(email)
            print("getting db")
            db = getdb(maindb)
            print("got db")
            print("dbbbbbb", db)
            print("getting cursur")
            cur = db.cursor()
            print("got cursur")
            gube=getUserByEmail(cur,udata['email'])
            print("gubee\n\n")
            print(gube)
            if gube:
              print("user already has email")
              return render_template("signup.html",udata=udata,msg="email already taken")
            print("email ready for use")
            try:
                ####gen user id
                print("adding to db ")
                date=datetime.now()
                str(date)
                userid=int(random()*100000000)
                print(c)
                print("\n\n userid",userid)
                print("inserting user data")
                print("udata \n\n")
                print(udata)
                print(date)
               # print(udata['pic'])
                print("inserting user data",type(userid))
                sname = udata['sname']
                fname=udata['fname']
                tname = udata['tname']
                email = udata['email']
                pnumber1 = udata['phone']
                level = udata['level']
                pic = udata['pic']
                pwds=udata['passwd']
                print([userid,fname,sname,tname,email,level,pnumber1,date,pwds])
                cur.execute(
                    "insert into Users (Id,FirstName,MiddleName,LastName,Email,Type,Dp,Phone1,Date,PassHash) values(?,?,?,?,?,?,?,?,?,?)",
                    (
                        [
                            userid,
                            udata['fname'],
                            udata['sname'],
                            udata['tname'],
                            udata['email'],
                            udata['level'],
                            udata['pic'],
                            udata['phone'],
                            date,
                            udata['passwd'],
                        ]
                    )
                )
                d=cur.execute("select * from Users").fetchall()
                for i in d:
                  print(i)
                print("user insert success")
                db.commit()
                cur.close()
                db.close()
                print("generating token")
                token=genToken(userid)
                print("generated token")
                print(token)
                print(udata['email'])
                print(userid)
                return render_template("token.html",token=token,email=udata['email'],userid=userid)
            except:
              ####check for id error
                print("failed to add user")
                db.rollback()
                cur.close()
                db.close()
            ###send verification token t o user email with login link
                return render_template("signup.html",udata=udata)
        except:
            print("failed to get cursor")
            return render_template("signup.html",udata=udata)
    else:
      return "use get"


def passHasher(passwd):
  passhash = generate_password_hash(passwd)
  if not passhash:
    return False
  return passhash

def genToken(idi):
  exp=3600
  s=Serializer(secret_key="kanye")
  x=s.dumps({'confirm':idi})
  print("\n\n x",x)
  return x

def getUUser(email, passwd):
    db = getdb(maindb)
    if not db:
        return "db error"
    try:
        print("getting cursur")
        cur = db.cursor()
        print("got cursor")
        print("getting user")
        us = cur.execute("select * from Account where Email=?", ([email])).fetchone()
        print("got user")
        print(type(us))
        if not us:
            print("no user with such email")
            cur.close()
            db.close()
            return "email not found"
        if us[9] == "False":
            print("your account is not verified")
            cur.close()
            db.close()
            return "not verified"
        ###verify passwd]\
        print(us[9])
        print("account verifies")
        print("verifying password")
        phash = us[6]
        print(us[6])
        print("pass hash", phash)
        if not verify_pass(phash, passwd):
            print("password incorrect")
            return "password incorrect"
        cur.close()
        db.close()
        print("formating user data")
        uer={'Id':us[0],'Name':us[1],'Email':us[2],'DP':us[3],'Role':us[4],'Status':us[5],'Password':us[6],'JoinDate':us[8]}
        print(uer)
        return uer
    except:
        print("db failure in getting user details")
        return "db error"

def verify_pass(phash, passwd):
    if check_password_hash(phash, passwd):
        print("password hash is a match")
        return True
    else:
        print("password hash is not a match")
        return False

@app.route('/login')
def login():
  return render_template('login.html',nloc='home')


@app.route('/forgot')
def forgot():
  return render_template("forgot.html")

@app.route('/create')
def create():
  udata={}
  ###query dp for pic with related album
  return render_template('create.html',udata=udata)



@sio.on('createaccount',namespace="/create")
def createaccount(data):
  username=''
  print("got data")
#  print(data)
  passhash=None
  dp=None
  email=None
  try:
    db=getdb(maindb)
    cur=db.cursor()
    print("got cursor")
    if data['email'] and data['email']!='':
      print("checking on email")
      try:
        istaken=cur.execute("select * from Account where Email=?",([data['email']])).fetchone()
        if istaken:
          print("email is already taken")
          ###emit this back to sign up page
          data={"Type":'Email','Msg':'email is already taken'}
          sio.emit('updatedata',data,room=request.sid,namespace="/create")
          cur.close()
          db.close()
          return
        else:
          print("email not taken checking if valid")
          ##check if email exists do it using js///check if valid //security
          email=data['email']
      except:
        print("failed to validate email")
        data={"Type":'Email','Msg':'failed to validate email'}
        sio.emit('updatedata',data,room=request.sid,namespace="/create")
        cur.close()
        db.close()
        return
      try:
        print("creating password hash")
        #passhash = passHasher(data['Passwd'])
        passhash = generate_password_hash(data['passwd'])
        if not passhash:
          print("failed to generate password hash")
          data={"Type":'Password','Msg':'failed to save password'}
          sio.emit('updatedata',data,room=request.sid,namespace="/create")
          db.close()
          return
        else:
          print("got password hash")
          print(passhash)
      except:
        print("failed to create password hash")
        data={"Type":'Password','Msg':'failed to save password'}
        sio.emit('updatedata',data,room=request.sid,namespace="/create")
        cur.close()
        db.close()
        return
      try:
        print("saving image")
        if data['myfile'] and data['myfile']!='':
          print('got profile  file obj')
          n=str(int(random()*100000)) +".jpeg"
          vs="./static/Images/DP/"+n
          print("after name")
          print(vs)
          fi=open(vs,"wb+")
          fi.write(data['myfile'])
          print("after write")
          fi.flush()
          fi.close()
          dp=n
          print("after save")

        else:
          print("no dp provided")
          dp="default.png"
      except:
        print("failed to save image")
      if passhash and email and data['fname']!='' and data['sname']!='':
        if cur:
          print("still got it")
        else:
          print("about to get it")
        try:
          ###save to db
          print("creating userid")
          userid=int(random()*10000000000)
          username=data['fname']+" "+data['sname']+" "+data['tname']
          date=datetime.ctime(datetime.now())
          print("inserting")
          print(username,date,userid,email,dp)
          cur.execute("insert into Account (Id,Name,Email,DP,Password,JoinDate) values(?,?,?,?,?,?)",([userid,username,email,dp,passhash,date]))
          print("done account")
          id=int(random()*10000000000)
          print(id)
          s=cur.execute("select * from PersonalDetails").fetchone()
          print(s)
          cur.execute("INSERT into PersonalDetails (FirstName,SecondName,ThirdName,AccountId) values(?,?,?,?)",([data['fname'],data['sname'],data['tname'],userid]))
          print('about to commit')
          db.commit()
          db.close()
          print("account creation success")
          ###redirect to confirmation token
        except:
          print("failed to create")
          data={"Type":'Error','Msg':'failed to create'}
          sio.emit('updatedata',data,room=request.sid,namespace="/create")
          db.rollback()
          db.close()
          return
        try:
          print("generating token")
          token=genToken(userid)
          print("generated token \n \n")
          token=token.decode('utf-8')
          print(type(token))
          print(token)
          print(email,userid)
          #v=token + "/" + email + "/" + userid
          #print('\n',v)
          data={"Type":'Success','Msg':'saved successfully','URL':'127.0.0.1:5000/','Token':token,'Userid':userid,'Email':email}
          sio.emit('updatedata',data,room=request.sid,namespace="/create")
          #####send email
          try:
           # sendE(token,email,userid)
            print("email sent")
            print(email,username)

            db.close()
            return render_template("thanku.html",email=email,names=username)
          except:
            print("failed to send email")
            return
        except:
          print("failed to create")
          data={"Type":'Error','Msg':'failed to create'}
          sio.emit('updatedata',data,room=request.sid,namespace="/create")
          db.rollback()
          db.close()
          return
  except:
    print("failed to get db")
    data={"Type":'Error','Msg':'failed to create'}
    sio.emit('updatedata',data,room=request.sid,namespace="/create")
    return

def confirmToken(userid,token):
  s=Serializer(secret_key="kanye")
  print("got serialiser")
  try:
    data=s.loads(token)
    print("got data",data)
    c=data['confirm']
    print(userid)
    userid=int(userid)
    print(type(userid))
    print(type(c))
    print(c)
    if c!=userid:
      print("did not get data")
      return False
    print("got data")
    return True
  except :
    return False

@app.route('/toke/<token>/<email>/<userid>')
def toke(token,email,userid):
  ##confirm token and update user db
  print(userid)
  print("eeeeemail \n",email)
  print("tokeeen \n",token)
  try:
    db=getdb(maindb)
    cur=db.cursor()
    print("eeeeemail \n",email)
    print("tokeeen \n",token)
    if not userid:
      return render_template("aboutus.html")
    if not confirmToken(userid,token):
      print("token does not confirm")
      return render_template("aboutus.html")
    ##update user verified status
    print("token confirmation sucessful")
    try:
      print("getting user data using userid")
      mydata=cur.execute("select * from Account where Id=?",([userid])).fetchone()
      if mydata:
        print("got user data")
        print(mydata)
        cur.execute("update Account set Verified=? where Id=?",(['True',userid]))
        db.commit()
      else:
        print("no user data not in accounts")
        db.rollback()
        db.close()
        return render_template("aboutus.html")
      try:
        ###create chats
        print("creating chats")
        print("\n\n useeeeer id",userid)
        id=userid
        chatCreate(db,cur,id)
        ###add
        try:
          print("creating edu and emergency")
          cur.execute("Insert into Education (UserId,Level) values (?,?)",([userid,'Primary']))
          print("created edu primary")
          cur.execute("Insert into Education (UserId,Level) values (?,?)",([userid,'Secondary']))
          print("created edu secondary")
          cur.execute("Insert into Education (UserId,Level) values (?,?)",([userid,'Tertiary']))
          print("created edu tertiary")
          cur.execute("Insert into Emergency (UserId) values (?)",([userid]))
          print("created emer 1")
          cur.execute("Insert into Emergency (UserId) values (?)",([userid]))
          print("created emer 2")
          db.commit()
          print("created edu and emergency")
        except:
          print("failed to creat edu and emergency")
          db.rollback()
        cur.close()
        db.close()
        print("chats created from accounts table")
        return redirect (url_for('login'))
      except :
        print("failed to create chatrooms")
        db.rollback()
        cur.close()
        db.close()
        return render_template("aboutus.html")
    except :
      db.rollback()
      db.close()
      print("failed to chnage verification status")
      return("failed to chnage verification status")
  except :
    print("db failed")
    return ("db failed")


@app.route("/signin", methods=["POST"])
def signin():
    email=""
    passwd=""
    conlik=""
    user=''

    if request.method == "POST":
        email = request.form["email"]
        passwd = request.form["passwd"]
        print("password,email")
        print(passwd,email)
        # get user with email
        if email=="" and passwd=="":
            print("no passwd or email")
            return ("no passwd or email")
        try:
            user = getUser(email, passwd)
            if user == "not verified":
                print("user not found")
                return "account not verified"
            elif user == "email not found":
                print("email not found")
                return render_template("signin.html",msg="email not found",email=email,passwd=passwd)
            elif user == "password incorrect":
                print("password incorrect")
                print("user found here ")
                print("printing user")
                print(user)
                return render_template("signin.html",msg="password incorrect",email=email,passwd=passwd)
            elif user=="db error":
                print("db error")
                return redirect("url_for(s)")
            id=user[0]
            session['User']=user
            print("usssser id,",id)
            session['Id']=id
            session['Role']=user[8]
            print(session['Id'])
            print(session['Role'])
            resp=make_response(redirect(url_for('getMessangerhome')))
            resp.set_cookie('Email',email)
            resp.set_cookie('Passwd',passwd)
            return resp
        except:
            print("db error")
            return("failed to get user")
    else:
        print("use get")
        return "use get"

@app.route("/signinn", methods=["POST"])
def signinn():
    email=""
    passwd=""
    conlik=""
    user=''
    nloc=''

    if request.method == "POST":
        email = request.form["email"]
        passwd = request.form["passwd"]
        nloc=request.form['nloc']
        print("password,email")
        print(passwd,email)
        # get user with email
        if email=="" and passwd=="":
            print("no passwd or email")
            print("\n new location",nloc)
            return render_template("login.html",msg="must enter valid email and password",email=email,passwd=passwd,nloc=nloc)
        try:
            user = getUUser(email, passwd)
            if user == "not verified":
                print("user not found")
                print("\n new location",nloc)

                return render_template("login.html",msg="account not verified",email=email,passwd=passwd,nloc=nloc)
            elif user == "email not found":
                print("email not found")
                print("\n new location",nloc)
                return render_template("login.html",msg="email not found",email=email,passwd=passwd,nloc=nloc)
            elif user == "password incorrect":
                print("password incorrect")
                print("user found here ")
                print("printing user")
                print(user)
                print("\n new location",nloc)
                return render_template("login.html",msg="password incorrect",email=email,passwd=passwd,nloc=nloc)
            elif user=="db error":
                print("db error")
                print("\n new location",nloc)
                return render_template("login.html",msg="Server error,Try agian in 2 minutes",email=email,passwd=passwd,nloc=nloc)
            session['User']=user
            print("\n added user to session \n\n")
            print("\n next location",nloc)
            if nloc==None:
              nloc='home'
            resp=make_response(redirect(url_for(nloc)))
            resp.set_cookie('Email',email)
            resp.set_cookie('Passwd',passwd)
            return resp
        except:
            print("db error")
            return("failed to get user")
    else:
        print("use get")
        return "use get"



@sio.on("userprofile",namespace="/myprofile")
def userprofile(id):
  user=''
  print("getting user profile")
  print("\n got id",id)
  if 'User' in session.keys():
    user=session['User']
    print("in session")
    data={'email':user['Email'],"DP":user['DP'],'Id':user['Id'],'level':user['Role'],'status':user['Status'], "password":'',"newpassword":'','desc':''}
    keys=list(data)
    data['Type']='Account'
    data['keys']=keys
    sio.emit("updatedata",data,room=request.sid,namespace="/myprofile")
    print("\n user level",user['Role'])
    print('\n')
    print(data)
    print("emited account data")
  else:
    print("not in session")
    return render_template('signup.html')
  userid=user["Id"]
  print(user)
  try:
    print("getting db")
    db=getdb(maindb)
    cur=db.cursor()
    try:
      if id!=user['Id']:
        print("data integrity error")
        return
      print("getting user data")
      per=cur.execute("select * from PersonalDetails where AccountId=(?)",([userid])).fetchall()
      med=cur.execute("select * from Medical where UserId=(?)",([userid])).fetchall()
      edu=cur.execute("select * from Education where UserId=(?)",([userid])).fetchall()
      emer=cur.execute("select * from Emergency where UserId=(?)",([userid])).fetchall()
      if med:
        print("got medical",med)
        for m in med:
          #send one at a time
          da={"Id":m[0],"Type":'Medical',"Name":m[3],"Kind":m[2],'Desc':m[5]}
          da['CMD']='Create'
          #da=json.dumps(da)
          print(da)
          sio.emit("updatedata",da,room=request.sid,namespace="/myprofile")
      else:
        print("no medical record")
      if edu:
        print("got education",edu)
        for m in edu:
          #send one at a time
          da={"Id":m[0],"Institution":m[2],"Level":m[3],'Type':'Education'}
          da['CMD']='Create'
          #da=json.dumps(da)
          print(da)
          sio.emit("updatedata",da,room=request.sid,namespace="/myprofile")
      else:
        print("no education records")
      if emer:
        print("got emergency",emer)
        k=1
        for m in emer:
          #send one at a time
          da={"name":m[2],"phone":m[3],"contact":m[4],"role":m[5],"member":m[6]}
          print(da)
          l=list(da)
          da['Id']=m[0]
          da['Index']=k
          da['keys']=l
          da['Type']="Emergency"
          k=k+1
          da['CMD']='Update'
          #da=json.dumps(da)
          print(da)
          sio.emit("updatedata",da,room=request.sid,namespace="/myprofile")
      else:
        print("no emergency records")
      if per:
        print("got personal",per)
        print("this is personal")
        for m in per:
          #send one at a time
          da={"Id":m[0],"Type":'Personal',"fname":m[1],"sname":m[2],"tname":m[3],'fcontact':m[4],'scontact':m[5],'sex':m[7],'dob':m[8],'mstatus':m[9],'occupation':m[10],'role':m[11]}
          k=list(da)
          print(da)
          print("\n",k)
          da['keys']=k
          sio.emit("updatedata",da,room=request.sid,namespace="/myprofile")
      else:
        print("no personal data")
      db.close()
      return
    except :
      db.close()
      print("failed to get user data")
      return("failed to get user data")
  except :
    print("failed to get db")
    return("failed to get db")

@app.route('/myProfile')
def myProfile():
  if not session['User']:
    print("not in session")
    autoLogin()
    if not session['User']:
      return render_template('signup.html')
  user=session['User']
  userid=user[0]
  print(user)
  if not userid:
    print("not in session")
    return render_template('signup.html')
  ##already has userid
  try:
    db=getdb(maindb)
    cur=db.cursor()
    try:
      user=cur.execute("select * from Users where Id=(?)",([userid])).fetchone()
      if not user:
        print("no such user please relogin")
        return "please relogin"
      print("my profile",user)
      ufname = user[1]
      usname = user[2]
      utname = user[3]
      upemail = user[4]
      udesc = user[5]
      upnumber1 = user[11]
      upnumber2 = user[12]
      udata = {
          "fname": user[1],
          "sname": user[2],
          "tname": user[3],
          "email": user[4],
          "desc": user[5],
          "phone1": user[11],
          "phone2": user[12],
      }
      print("formated data",udata)
      ###get medical and education and emergency
      med=cur.execute("select * from Medical where UserId=(?)",([userid])).fetchall()
      edu=cur.execute("select * from Education where UserId=(?)",([userid])).fetchall()
      emer=cur.execute("select * from Emergency where UserId=(?)",([userid])).fetchall()
      if med:
        for m in med:
          #send one at a time
          da={"Id":m[0],"UserId":m[1],"Type":m[2],"Name":m[3]}
      if edu:
        for m in edu:
          #send one at a time
          da={"Id":m[0],"UserId":m[1],"Institution":m[2],"Level":m[3]}
      if emer:
        for m in emer:
          #send one at a time
          da={"Id":m[0],"UserId":m[1],"First Name":m[2],"Second Name":m[3],"First Contact":m[4],"Second Conatct":m[5],"Role":m[6],"Member":m[7]}
    except :
      print("failed to get user data")
      return("failed to get user data")
  except :
    print("failed to get db")
    return("failed to get db")

@app.route('/chat/<int:id>/')
def otherProfile(id):
  print("in user profile")
  if not id:
    return "no id given"
  print("got user id")
  print("\n\n",id)
  print(session.keys())
  if 'User' in session.keys():
    print(session.keys())
    print("not in session")
    #autoLogin()
    if not 'User' in session.keys():
      print("still not in session")
      return "not in session"
    else:
      print("in session")
      print(session.keys())
  user=session['User']
  userid=user['Id']
  print(user)
  if not userid:
    print("not in session")
    return render_template('signup.html')
  ##already has userid
  try:
      udata={"Id":id}
      return render_template('otherprofile.html',udata=udata)
  except :
    print("failed ")
    return("failed ")


@sio.on("OtherProfile",namespace="/chat")
def userprofile(id):
  user=''
  print("getting user profile")
  print("\n got id",id)
  if session['User']:
    print("in session")
    user=session['User']
    #
  else:
    print("not in session")
    return render_template('signup.html')
  userid=user["Id"]
  print(user)
  try:
    print("getting db")
    db=getdb(maindb)
    cur=db.cursor()
    try:

      print("getting user data")
      ac=cur.execute("select * from Account where id=?",([id])).fetchone()
      per=cur.execute("select * from PersonalDetails where AccountId=(?)",([id])).fetchall()
      med=cur.execute("select * from Medical where UserId=(?)",([id])).fetchall()
      edu=cur.execute("select * from Education where UserId=(?)",([id])).fetchall()
      emer=cur.execute("select * from Emergency where UserId=(?)",([id])).fetchall()
      print("finished fetching")
      if ac:
        print("got account")
        keys=["Email","DP","Role","Status"]
        data={"Email":ac[2],"DP":ac[3],"Role":ac[4],"Status":ac[5],"Type":"Account","keys":keys}
        print(data)
        sio.emit("otherdata",data,room=request.sid,namespace="/chat")
      if med:
        print("got medical",med)
        for m in med:
          #send one at a time
          da={"Id":m[0],"Type":'Medical',"Name":m[3],"Kind":m[2],'Desc':m[5]}
          da['CMD']='Create'
          #da=json.dumps(da)
          print(da)
          sio.emit("otherdata",da,room=request.sid,namespace="/chat")
      else:
        print("no medical record")
      if edu:
        print("got education",edu)
        for m in edu:
          #send one at a time
          da={"Id":m[0],"Institution":m[2],"Level":m[3],'Type':'Education'}
          da['CMD']='Create'
          #da=json.dumps(da)
          print(da)
          sio.emit("otherdata",da,room=request.sid,namespace="/chat")
      else:
        print("no education records")
      if emer:
        print("got emergency",emer)
        k=1
        for m in emer:
          #send one at a time
          da={"name":m[2],"phone":m[3],"contact":m[4],"role":m[5],"member":m[6]}
          print(da)
          l=list(da)
          da['Id']=m[0]
          da['Index']=k
          da['keys']=l
          da['Type']="Emergency"
          k=k+1
          da['CMD']='Update'
          #da=json.dumps(da)
          print(da)
          sio.emit("otherdata",da,room=request.sid,namespace="/chat")
      else:
        print("no emergency records")
      if per:
        print("got personal",per)
        print("this is personal")
        for m in per:
          #send one at a time
          da={"Id":m[0],"Type":'Personal',"fname":m[1],"sname":m[2],"tname":m[3],'fcontact':m[4],'scontact':m[5],'sex':m[7],'dob':m[8],'mstatus':m[9],'occupation':m[10],'role':m[11]}
          k=list(da)
          print(da)
          print("\n",k)
          da['keys']=k
          sio.emit("otherdata",da,room=request.sid,namespace="/chat")
      else:
        print("no personal data")
      db.close()
      return
    except :
      db.close()
      print("failed to get user data")
      return("failed to get user data")
  except :
    print("failed to get db")
    return("failed to get db")
