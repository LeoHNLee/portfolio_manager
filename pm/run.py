import uiautomation as ui


acnt = ui.PaneControl(searchDepth=5, ClassName='GXWND', AutomationId='3779')
set_krw = ui.ButtonControl(searchDepth=5, Name='원화기준')