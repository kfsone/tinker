package main

import (
	"fmt"
	"time"
)

type versus struct {
	protocol string
	host string
	path string
	args string
}

func newVersus(prot string, host string, path string) *versus {
    c := versus{protocol: prot, host: host, path: path, args: ""}
	return &c
}

func (v *versus) uri() string {
    return v.protocol + "://" + v.host + "/" + v.path + v.args
}

func (v *versus) testURI() int {
    t := 0
    for i := 0; i < 24; i++ {
	  t += len(v.uri())
	}
	return t
}

func main() {
	var totalTime int64
	const runs int64 = 25000
	t := 0
    for i := int64(0); i < runs; i++ {
      start := time.Now()
      v := newVersus("https", "wiki.python.org", "moin/PythonSpeed/PerformanceTips")
	  t += v.testURI()
	  elapsed := time.Since(start)
	  totalTime += elapsed.Nanoseconds()
	}
	
	fmt.Printf("%d runs took %dns, average %d per loop\n", runs, totalTime, totalTime/runs)
	fmt.Printf("accumulated %d total characters.\n", t)
}
