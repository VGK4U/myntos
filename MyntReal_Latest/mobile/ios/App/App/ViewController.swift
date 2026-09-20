import UIKit
import Capacitor

class ViewController: CAPBridgeViewController {
    override open func capacitorDidLoad() {
        super.capacitorDidLoad()
        bridge?.registerPluginInstance(SecureStoragePlugin())
        bridge?.registerPluginInstance(IncomingCallPlugin())
        bridge?.registerPluginInstance(AudioRoutingPlugin())
        bridge?.registerPluginInstance(BackgroundLocationPlugin())
    }
}
