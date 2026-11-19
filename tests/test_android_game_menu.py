"""Production Back-event policy and activity menu launch guards; no Android task simulation."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def section(source, start, end):
    first = source.index(start)
    return source[first:source.index(end, first)]


class GameMenuTests(unittest.TestCase):
    def test_visible_menu_binding_is_scoped_to_a_running_game(self):
        javac, java = shutil.which('javac'), shutil.which('java')
        if not javac or not java:
            self.skipTest('JDK required')
        activity = (ROOT / 'games/totk/android/java/com/aure/totk/setup/SetupActivity.java').read_text()
        start = activity.index('    private void bindVisibleGame()')
        end = activity.index('\n    }', activity.index('    private void unbindVisibleGame()', start)) + len('\n    }')
        methods = activity[start:end].replace('android.util.Log.w', 'Log.w')
        source = '''
class ComponentName {} interface IBinder {}
interface ServiceConnection {
 void onServiceConnected(ComponentName name, IBinder service);
 void onServiceDisconnected(ComponentName name);
}
class Intent { Intent(Object owner, Class<?> cls) {} boolean getBooleanExtra(String key, boolean fallback) { return MenuBindingProbe.inGame; } }
class GameControlService {}
class Log { static void w(String a, String b, Throwable c) {} }
class GameLock { enum State { FREE, GAME, ERROR } }
class InstallState {
 static class Result { GameLock.State state = MenuBindingProbe.state; }
 static Result gameState(Object owner) { return new Result(); }
}
public class MenuBindingProbe {
 static boolean inGame, fail, bindResult = true;
 static GameLock.State state = GameLock.State.FREE;
 static final String EXTRA_GAME_TASK = "game";
 static final int BIND_AUTO_CREATE = 1, BIND_IMPORTANT = 64, BIND_ADJUST_WITH_ACTIVITY = 128;
 ServiceConnection visibleGameConnection;
 int bindings, unbindings, flags;
 Intent getIntent() { return new Intent(this, GameControlService.class); }
 boolean bindService(Intent intent, ServiceConnection connection, int options) {
  bindings++; flags = options; if (fail) throw new IllegalStateException(); return bindResult;
 }
 void unbindService(ServiceConnection connection) { unbindings++; }
''' + methods + '''
 static void require(boolean value) { if (!value) throw new AssertionError(); }
 public static void main(String[] args) {
  MenuBindingProbe menu = new MenuBindingProbe();
  menu.bindVisibleGame(); require(menu.bindings == 0);
  inGame = true; menu.bindVisibleGame(); require(menu.bindings == 0);
  state = GameLock.State.GAME; menu.bindVisibleGame();
  require(menu.bindings == 1 && menu.flags == 193 && menu.visibleGameConnection != null);
  menu.bindVisibleGame(); require(menu.bindings == 1);
  menu.unbindVisibleGame(); menu.unbindVisibleGame(); require(menu.unbindings == 1);
  bindResult = false; menu.bindVisibleGame(); require(menu.visibleGameConnection == null && menu.unbindings == 2);
  fail = true; menu.bindVisibleGame(); require(menu.visibleGameConnection == null && menu.unbindings == 3);
 }
}
'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'MenuBindingProbe.java'; path.write_text(source)
            result = subprocess.run([javac, '--release', '17', '-d', directory, str(path)],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            subprocess.run([java, '-cp', directory, 'MenuBindingProbe'], check=True, capture_output=True, text=True, timeout=30)

    def test_native_back_release_only_and_cancel(self):
        cc = shutil.which('cc')
        if not cc:
            self.skipTest('C compiler required')
        frontend = (ROOT / 'games/totk/runtime/frontend_android.c').read_text()
        body = section(frontend, 'static int game_menu_key(', 'static int handle_input(')
        source = '''#include <assert.h>
enum { AKEYCODE_BACK = 4, AKEY_EVENT_ACTION_DOWN = 0, AKEY_EVENT_ACTION_UP = 1, AKEY_EVENT_FLAG_CANCELED = 32 };
static int opens;
static void game_menu_open(void) { opens++; }
''' + body + '''
int main(void) {
    assert(!game_menu_key(108, 1, 0) && !opens); // controller Start remains guest input
    assert(game_menu_key(4, 0, 0) && !opens);
    assert(game_menu_key(4, 1, 32) && !opens);
    assert(game_menu_key(4, 1, 0) && opens == 1);
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as directory:
            c, binary = Path(directory) / 'menu.c', Path(directory) / 'menu'
            c.write_text(source)
            subprocess.run([cc, '-std=c11', '-Wall', '-Wextra', '-Werror', str(c), '-o', str(binary)],
                           check=True, capture_output=True, text=True, timeout=30)
            subprocess.run([str(binary)], check=True, capture_output=True, text=True, timeout=30)

    def test_activity_opens_existing_menu_once_and_keeps_game_alive(self):
        javac, java = shutil.which('javac'), shutil.which('java')
        if not javac or not java:
            self.skipTest('JDK required')
        activity = (ROOT / 'games/totk/android/java/com/aure/totk/TotkActivity.java').read_text()
        registration = section(activity, '    private void registerGameMenuBack()', '    public void showGameMenu()')
        self.assertIn('registerGameMenuBack();', section(activity, '    @Override protected void onCreate(', '    private boolean gameMenuOpen'))
        method = section(activity, '    public void showGameMenu()', '    /** Reuse/reparent the singleTask game,')
        source = '''
class NativeActivity { public void onBackPressed() {} }
class Log { static void w(String a, String b, Throwable c) {} }
class SetupActivity {
    static int opens; static boolean fail;
    static void openOnGame(Object owner) { if (fail) throw new IllegalStateException(); opens++; }
}
class OnBackInvokedDispatcher { static final int PRIORITY_DEFAULT = 0; }
class Dispatcher {
    Runnable callback;
    void registerOnBackInvokedCallback(int priority, Runnable action) { callback = action; }
}
public class MenuProbe extends NativeActivity {
    boolean resumed, gameMenuOpen, finishing;
    Dispatcher dispatcher = new Dispatcher();
    Dispatcher getOnBackInvokedDispatcher() { return dispatcher; }
    boolean isFinishing() { return finishing; }
''' + registration.replace('android.window.OnBackInvokedDispatcher.', 'OnBackInvokedDispatcher.') + method + '''
    static void require(boolean value) { if (!value) throw new AssertionError(); }
    public static void main(String[] args) {
        MenuProbe game = new MenuProbe();
        game.registerGameMenuBack(); require(game.dispatcher.callback != null);
        game.showGameMenu(); require(SetupActivity.opens == 0);
        game.resumed = true; game.dispatcher.callback.run(); require(SetupActivity.opens == 1);
        game.showGameMenu(); require(SetupActivity.opens == 1);
        game.gameMenuOpen = false; game.finishing = true;
        game.showGameMenu(); require(SetupActivity.opens == 1);
        game.finishing = false; SetupActivity.fail = true;
        game.showGameMenu(); require(!game.gameMenuOpen);
        SetupActivity.fail = false; game.showGameMenu(); require(SetupActivity.opens == 2);
    }
}
'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'MenuProbe.java'; path.write_text(source)
            subprocess.run([javac, '--release', '17', '-d', directory, str(path)],
                           check=True, capture_output=True, text=True, timeout=30)
            subprocess.run([java, '-cp', directory, 'MenuProbe'],
                           check=True, capture_output=True, text=True, timeout=30)


if __name__ == '__main__':
    unittest.main()
