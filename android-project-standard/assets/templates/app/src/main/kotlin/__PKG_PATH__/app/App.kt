// Application:Hilt 入口。启动时把 kernel 的日志 sink 路由到 android.util.Log(隐私纪律不变:
// payload 绝不进 Log)。

package __APP_ID__.app

import android.app.Application
import android.util.Log as AndroidLog
import __APP_ID__.kernel.Log
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class App : Application() {
    override fun onCreate() {
        super.onCreate()
        Log.sink = { line -> AndroidLog.i("app", line) }
    }
}
