// SPDX-License-Identifier: GPL-3.0-or-later
// Madeira Converter Exception: see LICENSE-EXCEPTION.md
// Offline diagnostic; shader files remain on the user's machine.
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iterator>
#include <vector>
extern "C" int madeira_uint_volumes_rewrite(const void*,size_t,void**,size_t*,char*,size_t);
int main(int argc,char **argv) {
    if(argc!=3) { fprintf(stderr,"usage: shader-volume-rewrite INPUT OUTPUT\n"); return 2; }
    std::ifstream file(argv[1],std::ios::binary);
    if(!file) return 3;
    std::vector<char> bytes((std::istreambuf_iterator<char>(file)),{});
    if(bytes.size()>64*1024*1024) return 4;
    void *out=nullptr; size_t len=0; char note[192];
    int result=madeira_uint_volumes_rewrite(bytes.data(),bytes.size(),&out,&len,note,sizeof note);
    printf("result=%d input=%zu output=%zu %s\n",result,bytes.size(),len,note);
    if(result==1) {
        std::ofstream output(argv[2],std::ios::binary);
        output.write(static_cast<char*>(out),len);
        bool okay=bool(output); free(out); return okay?0:5;
    }
    return result<0?1:0;
}
