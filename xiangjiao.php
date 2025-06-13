<?php


function fetchData($url)
{
    $ch = curl_init($url);
    global $cookie;
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, [
        "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Content-Type: application/json",
        "X-Cookie-Auth: $cookie"
    ]);
    curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, false);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    $sourceCode = curl_exec($ch);

    curl_close($ch);
    return $sourceCode;
}

$str_time = round(microtime(true) * 1000);

$latestdomain = 'https://wap2.muchangdian.com';
$cookie = '6662626233376637346165643362366363333866373837383938393261353561';

if (isset($_GET['filter'])) {
    $categories = [
        '最新' => 666,
        '全部分类' => 0,
        '香蕉盲盒' => 537,
        '香蕉新干线' => 552,
        '香蕉秀' => 549,
        '蓝光' => 434,
        '蕉点盛宴' => 551,
        '玩偶姐姐' => 449,
        '娜娜姐姐' => 532,
        '自拍偷拍' => 4,
        '制服诱惑' => 5,
        '清纯少女' => 6,
        '辣妹大奶' => 7,
        '女同专属' => 8,
        '素人演出' => 9,
        '角色扮演' => 10,
        '成人动漫' => 11,
        '人妻熟女' => 12,
        '变态另类' => 13,
        '经典伦理' => 14
    ];

    $categoriesArray = [];

    foreach ($categories as $title => $index) {
        $categoriesArray[] = [
            'type_id' => $index,
            'type_pid' => 0,
            'type_name' => $title
        ];
    }

    $response = [
        'class' => $categoriesArray,
        'filters' => (object)[],
        'jx' => 0,
        'list' => getResultArr("$latestdomain/vod/latest-0-0-0-0-0-0-0-0-0-1"),
        'parse' => 0
    ];

    header('Content-Type: application/json');
    echo json_encode($response);
} else if (isset($_GET['t']) && isset($_GET['pg'])) {
    $category = $_GET['t'];
    $page = $_GET['pg'];

    $specialCategories = [549, 551, 449, 532, 537, 552, 434];

    if (in_array($category, $specialCategories)) {
        $sourceUrl = "$latestdomain/special/detail/$category-" . ($page - 1);
    } elseif ($category == '666') {
        $sourceUrl = "$latestdomain/vod/latest-0-0-0-0-0-0-0-0-0-$page";
    } elseif ($category == '888') {
        $sourceUrl = "$latestdomain/minivod/topnew-0-0-0-0-0-0-0-0-0-0-$page";
    } else {
        $sourceUrl = "$latestdomain/vod/listing-$category-0-0-0-0-0-0-0-0-$page?timestamp=$str_time";
    }

    $videos = getResultArr($sourceUrl);
    $response['list'] = $videos;
    $response['jx'] = 0;
    $response['parse'] = 0;

    header('Content-Type: application/json');
    echo json_encode($response);
} else if (isset($_GET['wd'])) {
    $keyword = urlencode($_GET['wd']);
    $page = $_GET['pg'];
    $sourceUrl = "$latestdomain/search?page={$page}&wd={$keyword}&timestamp={$str_time}";

    $videos = getResultArr($sourceUrl);

    $response['list'] = $videos;
    $response['jx'] = 0;
    $response['parse'] = 0;

    header('Content-Type: application/json');
    echo json_encode($response);


} else if (isset($_GET['ids'])) {
    $id = $_GET['ids'];
    $sourceUrl = "$latestdomain/vod/reqplay/$id";
    $response = [];
    $sourceCode = fetchData($sourceUrl);
    $dataArr = json_decode($sourceCode, true);
    $playUrl = !empty($dataArr['data']['httpurl']) ? $dataArr['data']['httpurl'] : $dataArr['data']['httpurl_preview'];
    $playUrl = str_replace("?300", "", $playUrl);

    $list = [];
    $list[] = [
        'vod_id' => intval($id),
        'vod_name' => "片名_" . $id,
        'vod_pic' => "https://2025061117.aqsmimg183.sbs:10002/202403/ca/965fc03418d9f952ff3fb2d22bdbc4ca.jpg",
        'vod_year' => "0",
        'vod_area' => "地区",
        'vod_remarks' => "标记",
        'vod_actor' => "演员",
        'vod_director' => "导演",
        'vod_content' => "简介",
        'vod_play_from' => "香蕉视频",
        'vod_play_url' => "第01集$" . $playUrl
    ];
    $response['list'] = $list;
    $response['jx'] = 0;
    $response['parse'] = 0;

    header('Content-Type: application/json');
    echo json_encode($response);

} else if (isset($_GET['play'])) {

    $response = [
        "header" => (object)['User-Agent' => 'okhttp/3.12.0'],
        "url" => urldecode($_GET['play']),
        "parse" => 0,
        "jx" => 0,
    ];
    echo json_encode($response);
}

function getResultArr($sourceUrl)
{
    $sourceCode = fetchData($sourceUrl);
    $dataArray = json_decode($sourceCode, true);
    $videos = [];

    foreach ($dataArray['data']['vodrows'] as $video) {
        $videoItem = [
            'vod_id' => $video['vodid'] ?? "",
            'vod_name' => $video['title'] ?? "",
            'vod_pic' => $video['coverpic'] ?? "",
            'vod_remarks' => $video['createtime'] ?? "",
        ];
        $videos[] = $videoItem;

    }
    return !empty($videos) ? $videos : [];
}


