#include <stdio.h>
#include <string.h>
#include "maipai_tailnet_core.h"
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "line %d: %s\n", __LINE__, #x); return 1; } } while (0)
static int test(void) {
    mt_guard_t g={0}; CHECK(mt_guard_boot(&g,1)==1 && g.crashes==0); mt_guard_started(&g);
    CHECK(mt_guard_boot(&g,1)==1 && g.crashes==1); mt_guard_started(&g);
    CHECK(mt_guard_boot(&g,1)==1 && g.crashes==2); mt_guard_started(&g);
    CHECK(mt_guard_boot(&g,1)==0 && g.crashes==3); mt_guard_stable(&g); CHECK(mt_guard_boot(&g,1)==1 && g.crashes==0);
    char ipbuf[16]; mt_ip_to_str(0x6440aabb,ipbuf); CHECK(strcmp(ipbuf,"100.64.170.187")==0);
    CHECK(mt_parse_ip("100.127.255.255")==0x647fffff && mt_parse_ip("100.128.0.0")==0x64800000);
    CHECK(mt_parse_ip(NULL)==0 && mt_parse_ip("1.2.3.4x")==0 && mt_parse_ip("256.1.1.1")==0);
    CHECK(mt_is_tailnet_ip(0x64400000) && mt_is_tailnet_ip(0x647fffff) && !mt_is_tailnet_ip(0x64800000));
    CHECK(mt_peer_ok("100.64.0.1") && mt_peer_ok("100.127.255.255") && !mt_peer_ok("100.128.0.1") && !mt_peer_ok("0.0.0.0"));
    CHECK(mt_key_ok("tskey-123456") && mt_key_ok("tskey-Ab_09-z") && !mt_key_ok(NULL) && !mt_key_ok("badkey-123456") && !mt_key_ok("tskey-short!") );
    char key[122]; memset(key,'a',120); memcpy(key,"tskey-",6); key[120]='\0'; CHECK(mt_key_ok(key)); key[120]='a'; key[121]='\0'; CHECK(!mt_key_ok(key));
    CHECK(mt_start_decision(1,1,1,2,0,50000,30000)==MT_WAIT);
    CHECK(mt_start_decision(1,1,0,3,0,50000,30000)==MT_NEEDS_SETUP);
    CHECK(mt_start_decision(1,1,1,3,0,45999,30000)==MT_NO_MEMORY);
    CHECK(mt_start_decision(1,1,1,3,0,50000,23999)==MT_NO_MEMORY);
    CHECK(mt_start_decision(1,1,1,3,0,50000,24000)==MT_START);
    CHECK(mt_start_decision(1,0,1,3,0,50000,30000)==MT_OFF && mt_start_decision(0,1,1,3,1,50000,30000)==MT_OFF);
    mt_route_t route={0,0}; CHECK(mt_route_choose(&route,1,1)==0); mt_route_result(&route,0,1,1); CHECK(mt_route_choose(&route,1,1)==0);
    mt_route_result(&route,0,1,1); CHECK(mt_route_choose(&route,1,1)==1); mt_route_result(&route,1,1,1); CHECK(route.streak==0);
    CHECK(mt_route_choose(&route,0,1)==0 && route.streak==0); mt_route_result(&route,0,1,1); mt_route_result(&route,0,1,0); CHECK(route.route==0 && route.streak==2);
    char url[128]; CHECK(mt_url_with_host("wss://home.test:443/ws?q=1","100.64.0.2",url,sizeof(url)) && strcmp(url,"wss://100.64.0.2:443/ws?q=1")==0);
    CHECK(!mt_url_with_host("home.test","x",url,sizeof(url)) && !mt_url_with_host("ws:///x","x",url,sizeof(url)));
    CHECK(!mt_url_with_host("ws://x","a/b",url,sizeof(url)) && !mt_url_with_host("ws://x","a@b",url,sizeof(url)) && !mt_url_with_host("ws://x","long",url,4));
    mt_region_t reg={0,0}; CHECK(mt_region_wanted(&reg,100000,1,2,1)==2);
    CHECK(mt_region_wanted(&reg,100000,1,2,0)==0 && mt_region_wanted(&reg,100000,0,2,1)==0 && mt_region_wanted(&reg,100000,2,2,1)==0);
    mt_region_moved(&reg,100000); CHECK(mt_region_wanted(&reg,159999,1,2,1)==0 && mt_region_wanted(&reg,160000,1,2,1)==2);
    mt_region_moved(&reg,160000); mt_region_moved(&reg,220000); CHECK(mt_region_wanted(&reg,300000,1,2,1)==0);
    int64_t deadline=mt_prefer_deadline(0x90000000LL,60); CHECK(deadline==0x90000000LL+3600000 && mt_prefer_active(deadline,deadline-1) && !mt_prefer_active(deadline,deadline));
    CHECK(mt_prefer_deadline(100,0)==0 && mt_prefer_deadline(100,61)==0);
    CHECK(mt_prefer_route(0,1,1,1)==1 && mt_prefer_route(0,1,0,1)==0 && mt_prefer_route(1,0,1,1)==1);
    return 0;
}
int main(void) { CHECK(test()==0); puts("tailnet core ok"); return 0; }
