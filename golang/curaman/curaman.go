import (
    "bytes"
    "encoding/json"
    "errors"
    "fmt"
    "log"
    "io/ioutil"
    "net/http"
    "time"
)

/// API Endpoints
const CURA_API_AUTH                 := "/auth"
const CURA_API_AUTH_REQUEST         := CURA_API_AUTH + "/request"
const CURA_API_AUTH_CHECK           := CURA_API_AUTH + "/check"


// Translate an http.response to Map
func (response *http.Response) ToMap() mapping map[string]string {
    body, err := ioutil.ReadAll(response.Body)
    if err != nil {
        log.Fatal("Couldn't retrieve body")
    }
    mapping := make(map[string]string)
    json.Unmarshal(body, &mapping)
}

func wait_or_timeout(predicate func() (bool, error), timeout time.Duration) (bool, error) {   
    cutoff := time.After(timeout)
    tick := time.Tick(500 * time.Millisecond)
    for {
        select {
        case <- cutoff:
            return false, errors.New("timeout")
        case <- tick:
            complete, err := predicate()
            if err != nil {
                return false, err
            }
            if complete {
                return true, nil
            }
        }
    }
}


func get_request(api string, endpoint string, data string) (resp* http.Response, err error) {
    ///TODO: Verify api doesn't end with a / and endpoint does
    query := api + endpoint
    if data != "" {
        query += '/' + data
    }
    return http.Get(query)
}

func get_request_body(api string, endpoint string, data string) (body []uint8, err error) {
    response, err := get_request(api, endpoint, data)
    if err != nil {
        return "Request failed", err
    }
    body, err := ioutil.ReadAll(response.Body)
    if err != nil {
        return "Could not retrieve body", err
    }
    return body, nil
}

func get_json_request(api string, endpoint string, data string) (jsonData map[string]string, err error) {
    response, err := get_request(api, endpoint, data)
    if err != nil {
        return nil, err
    }
    return response_to_map(response), nil
}


func post_json_request(api string, endpoint string, data string) (respMap *map[string]string, err error) {
    jsonValue := bytes.NewBuffer([]uint8(data))
    response, err := http.Post(api + endpoint, "application/json", jsonValue)
    if err != nil {
        return nil, err
    }
    responseData := response_to_map(response)
    return &responseData, nil
}

type auth struct {
    App string `json:"application"`
    User string `json:"user"`
    Host string `json:"hostname"`
    Exclusion string `json:"exclusion_key"`
}

func get_auth(api string, application string, username string) (id string, err error) {
    id, key := "", ""
    data, _ := json.Marshal(&auth{App: application, User: username, Host: "", Exclusion: ""})
    jsonResponse, err := post_json_request(api, CURA_API_AUTH_REQUEST, string(data))
    return (*jsonResponse)["id"], nil
}

func check_auth(api string, id string) (success bool, err error) {
    response, err := get_json_request(api, CURA_API_AUTH_CHECK, id)
    if err != nil {
        return false, err
    }
    return response["message"] == "authorized", nil
}

type CuraSession struct {
    Address     string
    APIVersion  int
    Application string
    AuthID      string
}

func NewCuraSession(address string, application string) (session CuraSession) {
    session := CuraSession{Address: address, APIVersion: 1, Application: application, AuthID: ""}
    return session
}

func (c CuraSession) GetAPI() (api string) {
    return fmt.Sprintf("http://%s/api/v%d", c.Address, c.APIVersion)
}

func (c *CuraSession) RequestAuth(username string, timeout *time.Duration) (success bool, err error) {
    api := c.GetAPI()
    id, err := get_auth(api, c.Application, username)
    if err != nil { return false, err }
    fmt.Println("Got id: " + id)
    if timeout == nil {
        default_time := 30 * time.Second
        timeout = &default_time
    }
    success, err := wait_or_timeout(func() (bool, error) {
            approved, err := check_auth(api, id)
            if err != nil { return false, err }
            return approved, nil
        }, *timeout)
    if err != nil {
        return false, err
    } else if success {
        c.AuthID = id
    } else {
    }
    return success, nil
}

