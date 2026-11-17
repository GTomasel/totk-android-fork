package com.aure.totk;

import android.app.Service;
import android.content.Intent;
import android.os.Binder;
import android.os.IBinder;

/** A visible-menu binding preserves the paused game's process importance and keeps it out of the cached-app freezer while closing.
 * No game/runtime initialization: a bind racing with game exit may create this service in an otherwise empty process. */
public final class GameControlService extends Service {
    private final IBinder binder = new Binder();

    @Override public IBinder onBind(Intent intent) { return binder; }
}
