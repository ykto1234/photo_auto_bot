import sys
import os
import time
import datetime
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import re
import urllib
from urllib.parse import urlparse
import time
import schedule


import settings
import mylogger

# ログの定義
logger = mylogger.setup_logger(__name__)

# タスク終了フラグ
exit_flg = 0

def login(url, id, pw, id_sel, pw_sel, display):
    # chromeドライバーのパス
    chrome_path = "./driver/chromedriver.exe"

    # Selenium用オプション
    if display == '0':
        # 「0」が設定されている場合は、ブラウザを表示して実行する
        op = Options()
        op.add_argument("--disable-gpu")
        op.add_argument("--disable-extensions")
        op.add_argument("--proxy-server='direct://'")
        op.add_argument("--proxy-bypass-list=*")
        op.add_argument("--start-maximized")
        op.add_argument("--headless")
        #driver = webdriver.Chrome(chrome_options=op)
        driver = webdriver.Chrome(executable_path=chrome_path, chrome_options=op)
    else:
        # 「0」以外の場合は、ブラウザを非表示にして実行する
        #driver = webdriver.Chrome()
        driver = webdriver.Chrome(executable_path=chrome_path)

    # ログインページアクセス
    driver.get(url)
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, pw_sel))
    )
    driver.find_elements_by_css_selector(id_sel)[0].send_keys(id)
    driver.find_elements_by_css_selector(pw_sel)[0].send_keys(pw)
    driver.find_elements_by_css_selector(pw_sel)[0].send_keys(Keys.ENTER)

    return driver


def check_creator_page(driver, url, limit, interval):

    # ドメインのURLを取得
    domain_url = '{uri.scheme}://{uri.netloc}/'.format(uri=urllib.parse.urlparse(url))

    driver.get(url)

    # 公開前の写真数を保持しておく
    # ターゲット出現を待機
    POST_sel = "div.col-6.col-sm-4.post-col"
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, POST_sel))
    )
    soup = BeautifulSoup(driver.page_source, features="html.parser")
    before_post_list = soup.select(POST_sel)

    if exit_flg > 0:
        href = before_post_list[0].find_all("a")[0].get("href")
        # 写真ページに遷移
        logger.info("exit_flgが「" + str(exit_flg) + "」のため、一番最新の写真ページに遷移")
        driver.get(domain_url + href)
        return True

    logger.info("クリエイターページの監視開始")

    # ループ処理
    count = 0
    while True:

        # ターゲット出現を待機
        POST_sel = "div.col-6.col-sm-4.post-col"
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, POST_sel))
        )
        soup = BeautifulSoup(driver.page_source, features="html.parser")
        post_list = soup.select(POST_sel)

        print("....クリエイターページにて監視中.....")

        for post in post_list:
            remains_count = post.find_all("div", text=re.compile(".*残り.枚.*"))
            if len(remains_count) > 0:
                # 残り枚数がある場合
                href = post.find_all("a")[0].get("href")
                logger.info("売れ残りの写真があるため、対象の写真ページに遷移")
                logger.info("対象URL：" + domain_url + href)
                logger.info("監視回数：" + str(count))
                print("売れ残りの写真があるため、対象の写真ページに遷移します")
                # 写真ページに遷移
                driver.get(domain_url + href)
                return True

        if len(before_post_list) != len(post_list):
            # 公開前の写真数と異なっている場合、写真が公開されたと判断し、一番左上の写真ページに遷移
            href = post_list[0].find_all("a")[0].get("href")
            logger.info("写真が公開されたため、最新の写真ページに遷移")
            logger.info("対象URL：" + domain_url + href)
            logger.info("監視回数：" + str(count))
            print("写真が公開されたため、最新の写真ページに遷移します")
            # 写真ページに遷移
            driver.get(domain_url + href)
            return True

        if count > int(limit):
            return False

        time.sleep(float(interval))
        count += 1
        # ページを再読み込み
        driver.refresh()


def check_post_page(driver, limit, interval):
    # ループ処理
    count = 0
    while True:
        # 写真ページ
        # ターゲット出現を待機
        BUY_BTN_sel = "a.buy-button"
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, BUY_BTN_sel))
        )
        soup = BeautifulSoup(driver.page_source, features="html.parser")
        buy_count_list = soup.find_all("a", text=re.compile(".*購入する.*"))

        print("....写真ページにて監視中.....")

        if len(buy_count_list) > 0:
            logger.info("対象の写真の購入するボタンがクリックできるため、支払処理に遷移")
            logger.info("監視回数：" + str(count))
            print("対象の写真の購入するボタンがクリックできるため、支払処理に遷移します")
            driver.find_elements_by_css_selector(BUY_BTN_sel)[0].click()
            return True

        if count > int(limit):
            return False

        time.sleep(float(interval))
        count += 1
        # ページを再読み込み
        driver.refresh()


def pay_info_input(driver, card_num, card_expiry, card_expirm, card_cvc, billing_name):

    logger.info("支払処理を開始")

    # 決済に進むボタンを押下
    PAY_BTN_sel = "button#pay-button"
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, PAY_BTN_sel))
    )
    driver.find_elements_by_css_selector(PAY_BTN_sel)[0].click()

    print("支払処理を開始します")

    # カードナンバー入力
    CARDNUMBER_sel = "input#cardNumber"
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, CARDNUMBER_sel))
    )
    driver.find_elements_by_css_selector(CARDNUMBER_sel)[0].send_keys(card_num)

    # 有効期限入力
    if len(card_expiry) == 4:
        card_expiry = card_expiry[-2:]
    CARDEXPIREY_sel = "input#cardExpiry"
    driver.find_elements_by_css_selector(CARDEXPIREY_sel)[0].send_keys(card_expirm + card_expiry)

    # セキュリティコード入力
    CARDCVC_sel = "input#cardCvc"
    driver.find_elements_by_css_selector(CARDCVC_sel)[0].send_keys(card_cvc)

    # カード所有者情報入力
    BILLINGNAME_sel = "input#billingName"
    driver.find_elements_by_css_selector(BILLINGNAME_sel)[0].send_keys(billing_name)

    # 支払いボタン押下
    SUBMIT_BTN_sel = "button.SubmitButton.SubmitButton--complete"
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, SUBMIT_BTN_sel))
    )
    soup = BeautifulSoup(driver.page_source, features="html.parser")
    submit_count_list = soup.find_all("span", text=re.compile(".*支払う.*"))
    if len(submit_count_list) > 0:
        logger.info("支払うボタンが見つかりました")
        if PAY_CLICK_FLG == "1":
            logger.info("支払うボタンクリックフラグが「1：クリックする」のため、支払うボタンをクリック")
            print("支払うボタンクリックフラグが「1：クリックする」のため、支払うボタンをクリックします")
            driver.find_elements_by_css_selector(SUBMIT_BTN_sel)[0].click()
        else:
            logger.info("支払うボタンクリックフラグが「0：クリックしない」のため、支払うボタンをクリックしない")
            print("支払うボタンクリックフラグが「0：クリックしない」のため、支払うボタンをクリックしません")
    else:
        logger.error("支払うボタンが見つかりません")


def expexpiration_date_check():
    import datetime
    now = datetime.datetime.now()
    expexpiration_datetime = now.replace(month=2, day=7, hour=12, minute=0, second=0, microsecond=0)
    logger.info("有効期限：" + str(expexpiration_datetime))
    if now < expexpiration_datetime:
        return True
    else:
        return False

def main_job():
    print(datetime.datetime.now())
    print("監視開始時間になったため、処理を開始します")
    logger.info("時刻：" + str(datetime.datetime.now()))
    logger.info("監視開始時間になったため、処理を開始")


    # ログイン処理
    driver = login(URL, ID, PASS, ID_sel, PASS_sel, DISPLAY)

    BASE_URL = "https://only-five.jp/creators/"
    CREATOR_URL = BASE_URL + CREATOR_ID

    ret = check_creator_page(driver, CREATOR_URL, LIMIT_COUNT, INTERVAL)
    logger.debug("クリエイターページ監視結果：" + str(ret))

    if not ret:
        print("監視リトライ上限回数を超過したため、監視を終了します")
        logger.info("クリエイターページでの監視リトライ上限回数を超過したため、監視を終了")
        #sys.exit(0)
        global exit_flg
        exit_flg += 1
        driver.close()
        return

    ret2 = check_post_page(driver, LIMIT_COUNT, INTERVAL)
    logger.debug("写真ページ監視結果：" + str(ret2))

    if not ret2:
        print("監視リトライ上限回数を超過したため、監視を終了します")
        logger.info("写真ページでの監視リトライ上限回数を超過したため、監視を終了")
        #sys.exit(0)
        exit_flg += 1
        driver.close()
        return

    # 決済処理
    pay_info_input(driver, CARD_NUMBER, CARD_EXPIRE_YEAR, CARD_EXPIRE_MONTH, CARD_CVC, BILLING_NAME)
    logger.info("決済情報入力処理が完了")
    exit_flg +=2
    return

def cancel_wait_job():
    print(datetime.datetime.now())
    print("キャンセル待ち監視開始時間になったため、処理を開始します")
    logger.info("時刻：" + str(datetime.datetime.now()))
    logger.info("キャンセル待ち監視開始時間になったため、処理を開始")

    global exit_flg

    # ログイン処理
    driver = login(URL, ID, PASS, ID_sel, PASS_sel, DISPLAY)

    # キャンセル待ちのURLに遷移
    driver.get(CANCEL_WAIT_URL)

    ret = check_post_page(driver, LIMIT_COUNT, INTERVAL)
    logger.debug("写真ページ監視結果：" + str(ret))

    if not ret:
        print("監視リトライ上限回数を超過したため、終了します")
        #sys.exit(0)
        exit_flg += 2
        driver.close()
        return

    # 決済処理
    pay_info_input(driver, CARD_NUMBER, CARD_EXPIRE_YEAR, CARD_EXPIRE_MONTH, CARD_CVC, BILLING_NAME)
    print("処理が完了しました。")
    exit_flg +=2
    return

def check_value_empty(key_str, value_str):
    if value_str == None or value_str == "":
        # 値が存在しない場合
        raise ValueError("「" + key_str + "」の値が見つかりません。config.iniの設定を確認して下さい。")
    return

def check_value_date(key_str, date_str):
    try:
        datetime.datetime.strptime(date_str, '%Y/%m/%d')
    except ValueError:
        # 日付として正しくない場合
        raise ValueError("「" + key_str + "」の日付の形式はyyyy/MM/ddの形式で記載して下さい。config.iniの設定を確認して下さい。")
    return

def check_value_time(key_str, time_str):
    try:
        datetime.datetime.strptime(time_str, '%H:%M:%S')
    except ValueError:
        # 日付として正しくない場合
        raise ValueError("「" + key_str + "」の日付の形式はhh:mm:ssの形式で記載して下さい。config.iniの設定を確認して下さい。")
    return

def check_value_decimal(key_str, value_str):
    if not value_str.isdecimal():
        # 値が存在しない場合
        raise ValueError("「" + key_str + "」は半角数字で記載して下さい。config.iniの設定を確認して下さい。")
    return


if __name__ == '__main__':

    try:
        logger.debug("------------------------------------------------------------------------------------------------------------")
        logger.debug("------------------------------------------------------------------------------------------------------------")
        logger.info("プログラム起動開始")

        # 有効期限チェック
        # if not (expexpiration_date_check()):
        #     logger.info("有効期限切れため、プログラム起動終了")
        #     print("有効期限切れのため、処理を終了します")
        #     sys.exit(0)

        # 設定ファイル読み込み
        logger.debug("INIファイルのDEFAULTセクション読み込み")
        config_default = settings.read_config('DEFAULT')

        URL      = "https://only-five.jp/login" # <= スクレイピングしたい対象URL
        ID_sel   = "input#session_email"       # <= ログインID欄のCSSセレクタ
        PASS_sel = "input#session_password"               # <= ログインパスワード欄のCSSセレクタ

        # ブラウザ表示オプションの取得
        DISPLAY = config_default.get('DISPLAY')
        if DISPLAY == None or DISPLAY == "":
            # 値が存在しない場合
            DISPLAY = "1"

        # IDの取得
        ID = config_default.get('ID')
        check_value_empty('ID', ID)

        # パスワードの取得
        PASS = config_default.get('PASSWORD')
        check_value_empty('PASSWORD', PASS)

        # クリエイターのID取得
        CREATOR_ID = config_default.get('CREATOR_ID')
        check_value_empty('CREATOR_ID', CREATOR_ID)

        # インターバルの取得
        INTERVAL = config_default.get('INTERVAL')
        check_value_empty('INTERVAL', INTERVAL)

        # リトライ上限数の取得
        LIMIT_COUNT = config_default.get('LIMIT_COUNT')
        check_value_empty('LIMIT_COUNT', LIMIT_COUNT)
        check_value_decimal('LIMIT_COUNT', LIMIT_COUNT)

        # 公開開始日を取得
        #START_DATE = config_default.get('START_DATE')
        #check_value_empty('START_DATE', START_DATE)
        #check_value_date('START_DATE', START_DATE)

        # 公開開始時間を取得
        START_TIME = config_default.get('START_TIME')
        check_value_empty('START_TIME', START_TIME)
        check_value_time('START_TIME', START_TIME)

        # キャンセル待ち開始時間を取得
        CANCEL_WAIT_TIME = config_default.get('CANCEL_WAIT_TIME')
        check_value_empty('CANCEL_WAIT_TIME', CANCEL_WAIT_TIME)
        check_value_time('CANCEL_WAIT_TIME', CANCEL_WAIT_TIME)

        # 設定ファイル読み込み
        config_payinfo = settings.read_config('PAYINFO')

        # カード番号の取得
        CARD_NUMBER = config_payinfo.get('CARD_NUMBER')
        check_value_empty('CARD_NUMBER', CARD_NUMBER)
        check_value_decimal('CARD_NUMBER', CARD_NUMBER)

        # カード有効期限の取得
        CARD_EXPIRE_YEAR = config_payinfo.get('CARD_EXPIRE_YEAR')
        CARD_EXPIRE_MONTH = config_payinfo.get('CARD_EXPIRE_MONTH')
        check_value_empty('CARD_EXPIRE_YEAR', CARD_EXPIRE_YEAR)
        check_value_decimal('CARD_EXPIRE_YEAR', CARD_EXPIRE_YEAR)
        check_value_empty('CARD_EXPIRE_MONTH', CARD_EXPIRE_MONTH)
        check_value_decimal('CARD_EXPIRE_MONTH', CARD_EXPIRE_MONTH)

        # セキュリティ番号の取得
        CARD_CVC = config_payinfo.get('CARD_CVC')
        check_value_empty('CARD_CVC', CARD_CVC)
        check_value_decimal('CARD_CVC', CARD_CVC)

        # カード使用者名の取得
        BILLING_NAME = config_payinfo.get('BILLING_NAME')
        check_value_empty('BILLING_NAME', BILLING_NAME)

        # 支払うボタンクリックフラグ
        PAY_CLICK_FLG = config_payinfo.get('PAY_CLICK_FLG')
        if PAY_CLICK_FLG == None or PAY_CLICK_FLG == "":
            # 値が存在しない場合
            PAY_CLICK_FLG = "0"

        mode = input("起動モードを選択してください（1：公開開始前モード、2：キャンセル待ちモード）:")
        print("-----------------------------------------------------------------------------")
        mod_str = str(mode)
        if mode == "1":
            print("公開開始前モードで起動します")
            logger.info("公開開始前モードで起動")
            logger.debug("監視開始時間：" + START_TIME)
            logger.debug("キャンセル待ち開始時間：" + CANCEL_WAIT_TIME)
            logger.debug("インターバル：" + INTERVAL)
            logger.debug("リトライ上限回数：" + LIMIT_COUNT)
            logger.debug("支払いボタンクリックフラグ：" + PAY_CLICK_FLG)

            schedule.every().day.at(START_TIME).do(main_job)
            #schedule.every().day.at(CANCEL_WAIT_TIME).do(main_job)

            logger.info("監視開始時間まで待機開始")

            while True:
                print("....監視開始時間まで待機中.....")
                schedule.run_pending()
                time.sleep(1)
                #if exit_flg > 1:
                if exit_flg > 0:
                    #『続行するには何かキーを押してください . . .』と表示させる
                    os.system('PAUSE')
                    sys.exit(0)

        elif mode == "2":
            print("キャンセル待ちモードで起動します")
            logger.info("キャンセル待ちモードで起動")
            logger.debug("監視開始時間：" + START_TIME)
            logger.debug("キャンセル待ち開始時間：" + CANCEL_WAIT_TIME)
            logger.debug("インターバル：" + INTERVAL)
            logger.debug("リトライ上限回数：" + LIMIT_COUNT)
            logger.debug("支払いボタンクリックフラグ：" + PAY_CLICK_FLG)

            # キャンセル待ちURLを取得
            CANCEL_WAIT_URL = config_default.get('CANCEL_WAIT_URL')
            check_value_empty('CANCEL_WAIT_URL', CANCEL_WAIT_URL)
            logger.debug("キャンセル待ちURL：" + CANCEL_WAIT_URL)

            schedule.every().day.at(CANCEL_WAIT_TIME).do(cancel_wait_job)

            logger.info("監視開始時間まで待機開始")

            while True:
                print("....監視開始時間まで待機中.....")
                schedule.run_pending()
                time.sleep(1)
                if exit_flg > 0:
                    #『続行するには何かキーを押してください . . .』と表示させる
                    os.system('PAUSE')
                    sys.exit(0)
        else:
            print("モードは1か2を指定してください。")
            logger.debug("モードで１か２以外を選択されたため、プログラムの起動終了")

    except Exception as err:
        print("処理が失敗しました。")
        print(err)
        logger.error("処理が失敗しました。")
        logger.error(err)
        logger.error(traceback.format_exc())
        #『続行するには何かキーを押してください . . .』と表示させる
        os.system('PAUSE')
