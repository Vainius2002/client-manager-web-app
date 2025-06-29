import eventlet
eventlet.monkey_patch()

from info import web as app, socketio

if __name__ == "__main__":
    socketio.run(app)
