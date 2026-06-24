// 最小 Compose 入口。UI 只做渲染与编排;领域逻辑在领域 feature module(经注入的 :domain port)。

package __APP_ID__.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface {
                    Greeting(name = "__APP_ID__")
                }
            }
        }
    }
}

@Composable
private fun Greeting(name: String) {
    Text(text = "Hello, $name")
}
