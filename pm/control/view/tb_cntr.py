def plus(tb, amt):
    old = tb.toPlainText()
    new = int(old) + amt
    tb.setPlainText(str(new))