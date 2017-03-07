from databroker_browser.qt import BrowserWindow, CrossSection, StackViewer


search_result = lambda h: "{start[plan_name]} ['{start[uid]:.6}']".format(**h)
text_summary = lambda h: "This is a {start[plan_name]}.".format(**h)


def fig_dispatch(header, factory):
    plan_name = header['start']['plan_name']
    if 'image_det' in header['start']['detectors']:
        fig = factory('Image Series')
        cs = CrossSection(fig)
        sv = StackViewer(cs, db.get_images(header, 'image'))
    elif len(header['start'].get('motors', [])) == 1:
        motor, = header['start']['motors']
        main_det, *_ = header['start']['detectors']
        fig = factory("{} vs {}".format(main_det, motor))
        ax = fig.gca()
        lp = LivePlot(main_det, motor, ax=ax)
        db.process(header, lp)


def browse():
    return BrowserWindow(db, fig_dispatch, text_summary, search_result)
